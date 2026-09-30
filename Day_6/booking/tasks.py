import logging

from celery import shared_task
from django.utils import timezone

from . import broker
from .exceptions import BrokerTemporaryError, GatewayTemporaryError, TemporaryDatabaseError
from .models import Booking
from .services import booking as booking_service
from .services import inbox, outbox
from .services import payments as payment_service

log = logging.getLogger(__name__)

RETRYABLE = (GatewayTemporaryError, TemporaryDatabaseError)


@shared_task(bind=True, autoretry_for=RETRYABLE, retry_backoff=2, retry_backoff_max=300,
             retry_jitter=True, max_retries=8)
def initiate_payment(self, booking_id):
    """Safe to run twice: no-op unless payment is still INITIATED; gateway call is idempotent."""
    return payment_service.initiate_payment(booking_id)


@shared_task(bind=True, autoretry_for=(TemporaryDatabaseError,), retry_backoff=1,
             retry_backoff_max=60, retry_jitter=True, max_retries=5)
def publish_outbox_events(self):
    """Outbox relay. AT-LEAST-ONCE: crash between publish and mark_published => re-published
    with the same message_id; consumers de-duplicate on it."""
    sent = failed = 0
    for ev in outbox.claim_batch():
        try:
            broker.publish(message_id=ev.id, event_type=ev.event_type,
                           aggregate_id=ev.aggregate_id, payload=ev.payload)
        except BrokerTemporaryError as exc:
            outbox.mark_failed(ev, exc)
            failed += 1
            continue
        outbox.mark_published(ev.id)
        sent += 1
    return {"sent": sent, "failed": failed}


@shared_task
def redispatch_stuck_payments():
    ids = payment_service.stuck_payment_booking_ids()
    for bid in ids:
        initiate_payment.delay(str(bid))
    return len(ids)


@shared_task
def expire_stale_bookings():
    ids = list(Booking.objects.filter(
        status=Booking.Status.PENDING_PAYMENT, expires_at__lt=timezone.now()
    ).values_list("id", flat=True)[:200])
    expired = 0
    for bid in ids:
        try:
            expired += bool(booking_service.expire_booking(bid))
        except TemporaryDatabaseError:
            log.warning("expire_booking(%s) hit temp db error; next run retries", bid)
    return expired


@shared_task(bind=True, autoretry_for=(TemporaryDatabaseError,), retry_backoff=2, max_retries=5)
def consume_booking_confirmed(self, message):
    """Reference consumer: duplicate deliveries are dropped by the inbox table."""
    def handle():
        log.info("sending ticket confirmation for booking %s", message["data"]["booking_id"])
    return inbox.process_once(message["message_id"], "ticket-notifier", handle)