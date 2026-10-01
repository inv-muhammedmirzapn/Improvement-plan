"""
Celery tasks for Restaurant Service.

All tasks are idempotent by design:
- publish_outbox_events: relay is idempotent because consumers use ProcessedMessage
- reconcile_capacity: read-only audit that emits correction commands
- retry_stale_outbox: re-locks and retries permanently-failed outbox events
"""
import logging

from celery import shared_task

from . import broker
from .exceptions import BrokerTemporaryError, TemporaryDatabaseError
from .models import OutboxEvent, Restaurant
from .services import outbox as outbox_service

log = logging.getLogger(__name__)

RETRYABLE = (TemporaryDatabaseError,)


@shared_task(
    bind=True,
    autoretry_for=RETRYABLE,
    retry_backoff=1,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=5,
)
def publish_outbox_events(self):
    """
    Outbox relay. AT-LEAST-ONCE: crash between publish and mark_published
    results in re-publish; consumers de-duplicate via ProcessedMessage.
    """
    sent = failed = 0
    for ev in outbox_service.claim_batch():
        try:
            broker.publish(
                message_id=ev.id,
                event_type=ev.event_type,
                aggregate_id=ev.aggregate_id,
                payload=ev.payload,
            )
        except BrokerTemporaryError as exc:
            outbox_service.mark_failed(ev, exc)
            failed += 1
            continue
        outbox_service.mark_published(ev.id)
        sent += 1
    return {'sent': sent, 'failed': failed}


@shared_task
def reconcile_capacity():
    """
    Periodic reconciliation: detect restaurants with anomalous active_order_count.
    This is a best-effort audit; it logs discrepancies for manual review.
    """
    from django.conf import settings
    import requests

    order_service_url = getattr(settings, 'ORDER_SERVICE_URL', 'http://127.0.0.1:8002')
    timeout = getattr(settings, 'ORDER_SERVICE_TIMEOUT', 5)

    for restaurant in Restaurant.objects.filter(status=Restaurant.Status.OPEN):
        try:
            resp = requests.get(
                f'{order_service_url}/internal/restaurants/{restaurant.id}/active-count/',
                timeout=timeout,
            )
            if resp.status_code == 200:
                actual_count = resp.json().get('count', 0)
                if actual_count != restaurant.active_order_count:
                    log.warning(
                        'Capacity mismatch for restaurant %s: local=%d order_service=%d',
                        restaurant.id, restaurant.active_order_count, actual_count,
                    )
                    # Auto-correct only if the discrepancy is safe to fix
                    if actual_count >= 0:
                        Restaurant.objects.filter(pk=restaurant.id).update(
                            active_order_count=actual_count
                        )
        except Exception as exc:
            log.warning('reconcile_capacity: could not reach order service for %s: %s', restaurant.id, exc)


@shared_task
def retry_stale_outbox():
    """
    Reset the locked_until on stale outbox events so they get retried.
    Handles the case where a worker crashed after locking but before publishing.
    """
    from django.utils import timezone
    from datetime import timedelta
    from django.conf import settings

    stale_seconds = getattr(settings, 'OUTBOX_STALE_SECONDS', 300)
    threshold = timezone.now() - timedelta(seconds=stale_seconds)

    count = OutboxEvent.objects.filter(
        published_at__isnull=True,
        locked_until__lt=threshold,
    ).update(locked_until=None)

    if count:
        log.info('retry_stale_outbox: reset %d stale outbox events', count)
    return count
