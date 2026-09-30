
import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .. import gateway
from ..db_retry import retry_on_db_error
from ..exceptions import GatewayPermanentError, PaymentNotFound
from ..models import Booking, BookingSeat, Payment, Seat
from . import outbox
from .booking import release_seats

log = logging.getLogger(__name__)


def initiate_payment(booking_id):
    """Celery-side step. Gateway call happens with NO transaction open.
    GatewayTemporaryError propagates so Celery autoretries with backoff."""
    payment = Payment.objects.filter(booking_id=booking_id).first()
    if payment is None or payment.status != Payment.Status.INITIATED:
        return "skipped"                                # duplicate task execution -> no-op
    if not Booking.objects.filter(pk=booking_id, status=Booking.Status.PENDING_PAYMENT).exists():
        return "skipped"

    try:
        payload = gateway.create_payment(
            reference=payment.gateway_reference, amount=payment.amount,
            currency=payment.currency, idempotency_key=payment.gateway_reference,
        )
    except GatewayPermanentError as exc:
        log.error("gateway rejected payment %s: %s", payment.gateway_reference, exc)
        fail_payment(booking_id, reason="gateway_rejected")
        return "failed"

    # Compare-and-set: a webhook that already advanced the payment wins.
    Payment.objects.filter(pk=payment.pk, status=Payment.Status.INITIATED).update(
        status=Payment.Status.PENDING, gateway_payload=payload, updated_at=timezone.now()
    )
    return "initiated"


@retry_on_db_error()
def process_payment_webhook(*, gateway_reference, status):
    """Idempotent, state-machine-guarded webhook handler. Returns a short outcome string."""
    booking_id = (
        Payment.objects.filter(gateway_reference=gateway_reference)
        .values_list("booking_id", flat=True).first()
    )
    if booking_id is None:
        raise PaymentNotFound(gateway_reference)

    with transaction.atomic():
        # Lock order: Booking -> Payment -> Seats. Concurrent duplicates queue here; the 2nd
        # one sees the final state and becomes a no-op.
        booking = Booking.objects.select_for_update().get(pk=booking_id)
        payment = Payment.objects.select_for_update().get(booking_id=booking_id)

        if status == "SUCCESS":
            return _apply_success(booking, payment)
        return _apply_failure(booking, payment)


def _event_payload(booking, payment, extra=None):
    seat_ids = list(BookingSeat.objects.filter(booking=booking).values_list("seat_id", flat=True))
    data = {
        "booking_id": str(booking.id), "user_id": booking.user_id, "event_id": str(booking.event_id),
        "seat_ids": sorted(str(s) for s in seat_ids), "amount": str(payment.amount),
        "gateway_reference": payment.gateway_reference,
    }
    data.update(extra or {})
    return data


def _apply_success(booking, payment):
    P, B = Payment.Status, Booking.Status
    if payment.status == P.SUCCEEDED:
        return "duplicate"
    if payment.status == P.FAILED:
        log.warning("SUCCESS after FAILED for %s ignored", payment.gateway_reference)
        return "ignored_invalid_transition"

    payment.status = P.SUCCEEDED
    payment.save(update_fields=["status", "updated_at"])

    if booking.status == B.PENDING_PAYMENT:
        seat_ids = list(BookingSeat.objects.filter(booking=booking).values_list("seat_id", flat=True))
        updated = Seat.objects.filter(
            id__in=seat_ids, status=Seat.Status.RESERVED
        ).update(status=Seat.Status.SOLD)
        expected = len(seat_ids)
        if updated != expected:   # rolls back loudly if invariants are ever broken
            raise RuntimeError(f"seat state corrupted for booking {booking.id}")
        booking.status = B.CONFIRMED
        booking.save(update_fields=["status", "updated_at"])
        outbox.enqueue(aggregate_id=booking.id, event_type="BookingConfirmed",
                       payload=_event_payload(booking, payment))
        return "confirmed"

    if booking.status == B.CONFIRMED:
        return "duplicate"

    # Money arrived but the hold was already released: record payment, request a refund.
    booking.status = B.REFUND_REQUIRED
    booking.save(update_fields=["status", "updated_at"])
    outbox.enqueue(aggregate_id=booking.id, event_type="PaymentRefundRequired",
                   payload=_event_payload(booking, payment, {"reason": "booking_not_pending"}))
    return "refund_required"


def _apply_failure(booking, payment):
    P, B = Payment.Status, Booking.Status
    if payment.status in (P.SUCCEEDED, P.FAILED):
        return "duplicate" if payment.status == P.FAILED else "ignored_invalid_transition"
    payment.status = P.FAILED
    payment.save(update_fields=["status", "updated_at"])
    if booking.status == B.PENDING_PAYMENT:
        release_seats(booking)
        booking.status = B.CANCELLED
        booking.save(update_fields=["status", "updated_at"])
        outbox.enqueue(aggregate_id=booking.id, event_type="BookingFailed",
                       payload=_event_payload(booking, payment))
    return "failed"


@retry_on_db_error()
def fail_payment(booking_id, reason):
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=booking_id)
        payment = Payment.objects.select_for_update().get(booking_id=booking_id)
        if payment.status in (Payment.Status.INITIATED, Payment.Status.PENDING):
            _apply_failure(booking, payment)


def stuck_payment_booking_ids(older_than_seconds=30, limit=200):
    cutoff = timezone.now() - timedelta(seconds=older_than_seconds)
    return list(
        Payment.objects.filter(
            status=Payment.Status.INITIATED, created_at__lt=cutoff,
            booking__status=Booking.Status.PENDING_PAYMENT,
        ).values_list("booking_id", flat=True)[:limit]
    )