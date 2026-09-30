import hashlib
import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from ..db_retry import retry_on_db_error
from ..exceptions import EventNotFound, EventNotOpen, IdempotencyConflict, SeatsUnavailable
from ..models import Booking, BookingSeat, Event, Payment, Seat
from . import outbox

log = logging.getLogger(__name__)


def _request_hash(user_id, event_id, seat_ids):
    raw = f"{user_id}|{event_id}|{','.join(sorted(str(s) for s in seat_ids))}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _replay(existing, req_hash):
    if existing.request_hash != req_hash:
        raise IdempotencyConflict("idempotency_key was already used with a different request.")
    return existing


def _enqueue_payment(booking_id):
    """Runs only after COMMIT. If the broker is down or we crash here, the
    `redispatch_stuck_payments` sweeper picks the INITIATED payment up later."""
    try:
        from ..tasks import initiate_payment
        initiate_payment.delay(str(booking_id))
    except Exception:  # noqa: BLE001 - must never fail the request after commit
        log.exception("could not enqueue initiate_payment for %s; sweeper will recover", booking_id)


@retry_on_db_error()
def create_booking(*, user_id, event_id, seat_ids, idempotency_key):
    """Returns (booking, created). Lock order everywhere: Booking -> Payment -> Seats (by id)."""
    seat_ids = sorted(set(seat_ids))
    req_hash = _request_hash(user_id, event_id, seat_ids)

    # Fast path for replays: plain read, no transaction, no locks.
    existing = Booking.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return _replay(existing, req_hash), False

    hold_seconds = getattr(settings, "BOOKING_HOLD_SECONDS", 600)

    try:
        with transaction.atomic():
            # (1) Insert booking FIRST. UNIQUE(idempotency_key) serializes concurrent duplicates:
            #     the 2nd inserter blocks until the 1st commits/rolls back.
            booking = Booking.objects.create(
                user_id=user_id,
                event_id=event_id,
                idempotency_key=idempotency_key,
                request_hash=req_hash,
                status=Booking.Status.PENDING_PAYMENT,
                expires_at=timezone.now() + timedelta(seconds=hold_seconds),
            )

            event = Event.objects.filter(pk=event_id).first()
            if event is None:
                raise EventNotFound()
            if event.status != Event.Status.OPEN:
                raise EventNotOpen()

            # (2) Pessimistic row locks in deterministic id order (no deadlocks between
            #     {10,11} and {10,12}).
            seats = list(
                Seat.objects.select_for_update()
                .filter(event_id=event_id, id__in=seat_ids)
                .order_by("id")
            )
            found = {s.id for s in seats}
            missing = [s for s in seat_ids if s not in found]
            taken = [s.id for s in seats if s.status != Seat.Status.AVAILABLE]
            if missing or taken:
                # Raising inside atomic() rolls back everything: all-or-nothing.
                raise SeatsUnavailable(missing + taken)

            Seat.objects.filter(pk__in=found).update(status=Seat.Status.RESERVED)
            # (3) DB-level backstop: UNIQUE(active_seat)
            BookingSeat.objects.bulk_create(
                [BookingSeat(booking=booking, seat=s, active_seat=s) for s in seats]
            )
            amount = sum((s.price for s in seats), Decimal("0.00"))
            # (4) One payment per booking (OneToOne). Reference doubles as gateway idempotency key.
            Payment.objects.create(
                booking=booking,
                gateway_reference=f"BK-{booking.id.hex}",
                amount=amount,
                status=Payment.Status.INITIATED,
            )
            transaction.on_commit(lambda: _enqueue_payment(booking.id))
    except IntegrityError:
        # Lost the race on UNIQUE(idempotency_key) (or UNIQUE(active_seat) as a backstop).
        existing = Booking.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return _replay(existing, req_hash), False
        raise SeatsUnavailable(seat_ids)

    return booking, True


@retry_on_db_error()
def expire_booking(booking_id):
    """Release seats of an unpaid booking whose hold has run out."""
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=booking_id)
        if booking.status != Booking.Status.PENDING_PAYMENT or booking.expires_at > timezone.now():
            return False
        payment = Payment.objects.select_for_update().get(booking=booking)
        if payment.status == Payment.Status.SUCCEEDED:
            return False
        release_seats(booking)
        booking.status = Booking.Status.EXPIRED
        booking.save(update_fields=["status", "updated_at"])
        payment.status = Payment.Status.EXPIRED
        payment.save(update_fields=["status", "updated_at"])
        outbox.enqueue(
            aggregate_id=booking.id,
            event_type="BookingExpired",
            payload={"booking_id": str(booking.id), "event_id": str(booking.event_id)},
        )
    return True


def release_seats(booking):
    """Caller holds the booking lock. Frees seats and clears the unique 'active hold' marker."""
    seat_ids = list(
        BookingSeat.objects.filter(booking=booking).values_list("seat_id", flat=True)
    )
    list(Seat.objects.select_for_update().filter(pk__in=seat_ids).order_by("id"))
    Seat.objects.filter(pk__in=seat_ids, status=Seat.Status.RESERVED).update(status=Seat.Status.AVAILABLE)
    BookingSeat.objects.filter(booking=booking).update(active_seat=None)