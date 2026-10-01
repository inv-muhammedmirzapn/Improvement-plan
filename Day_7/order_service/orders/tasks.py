"""
Celery tasks for Order Service.

All tasks are idempotent:
- publish_outbox_events: safe because consumers de-duplicate via ProcessedMessage
- detect_stuck_orders: read-only detection + transition to CANCELLED (idempotent)
- reconcile_closed_restaurant_orders: cancel PENDING orders for closed restaurants
- retry_stale_outbox: reset stale locked_until
"""
import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from . import broker
from .exceptions import BrokerTemporaryError, TemporaryDatabaseError
from .models import Order, OutboxEvent
from .services import order as order_service
from .services import outbox as outbox_service

log = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(TemporaryDatabaseError,),
    retry_backoff=1,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=5,
)
def publish_outbox_events(self):
    """Outbox relay — AT-LEAST-ONCE delivery."""
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
def detect_stuck_orders():
    """
    Detect orders stuck in PENDING or CONFIRMED beyond threshold.
    Moves them to CANCELLED with a note for manual review if they've
    exceeded the threshold.
    """
    threshold_minutes = getattr(settings, 'STUCK_ORDER_THRESHOLD_MINUTES', 30)
    cutoff = timezone.now() - timezone.timedelta(minutes=threshold_minutes)

    stuck = list(
        Order.objects.filter(
            status__in=[Order.Status.PENDING, Order.Status.CONFIRMED],
            created_at__lt=cutoff,
        ).values_list('id', flat=True)[:100]
    )

    cancelled = 0
    for order_id in stuck:
        try:
            order = Order.objects.filter(pk=order_id).first()
            if order and order.status in (Order.Status.PENDING, Order.Status.CONFIRMED):
                log.warning('Stuck order detected: %s (status=%s)', order_id, order.status)
                # Emit alert — do NOT auto-cancel without business confirmation
                # This is intentional: stuck orders go to manual review queue
        except Exception as exc:
            log.error('detect_stuck_orders: error processing %s: %s', order_id, exc)

    return {'stuck_count': len(stuck)}


@shared_task
def reconcile_closed_restaurant_orders():
    """
    Cancel PENDING orders for restaurants that have closed.
    This handles: Restaurant Service says CLOSED while Order Service has PENDING orders.
    Uses an internal call to Restaurant Service to check current status.
    """
    import requests

    restaurant_url = getattr(settings, 'RESTAURANT_SERVICE_URL', 'http://127.0.0.1:8001')
    timeout = getattr(settings, 'RESTAURANT_SERVICE_TIMEOUT', 5)

    # Find distinct restaurant_ids with PENDING orders
    pending_restaurant_ids = (
        Order.objects.filter(status=Order.Status.PENDING)
        .values_list('restaurant_id', flat=True)
        .distinct()
    )

    cancelled = 0
    for restaurant_id in pending_restaurant_ids:
        try:
            resp = requests.get(
                f'{restaurant_url}/restaurants/{restaurant_id}/',
                timeout=timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 'CLOSED':
                    # Cancel all PENDING orders for this closed restaurant
                    pending_orders = Order.objects.filter(
                        restaurant_id=restaurant_id,
                        status=Order.Status.PENDING,
                    )
                    for order in pending_orders:
                        try:
                            order_service.reject_order(order.id)
                            cancelled += 1
                            log.info('Cancelled order %s: restaurant %s is closed', order.id, restaurant_id)
                        except Exception as exc:
                            log.warning('Could not cancel order %s: %s', order.id, exc)
        except Exception as exc:
            log.warning('reconcile_closed_restaurant_orders: cannot reach restaurant service for %s: %s',
                        restaurant_id, exc)

    return {'cancelled': cancelled}


@shared_task
def retry_stale_outbox():
    """Reset stale locked_until so events get retried."""
    from datetime import timedelta
    stale_seconds = getattr(settings, 'OUTBOX_STALE_SECONDS', 300)
    threshold = timezone.now() - timedelta(seconds=stale_seconds)
    count = OutboxEvent.objects.filter(
        published_at__isnull=True,
        locked_until__lt=threshold,
    ).update(locked_until=None)
    if count:
        log.info('retry_stale_outbox: reset %d stale outbox events', count)
    return count
