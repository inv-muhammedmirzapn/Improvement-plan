"""
Outbox service for Order Service. Same pattern as Restaurant Service.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from ..models import OutboxEvent

log = logging.getLogger(__name__)


def claim_batch():
    batch_size = getattr(settings, 'OUTBOX_BATCH_SIZE', 50)
    lease_seconds = getattr(settings, 'OUTBOX_LEASE_SECONDS', 60)
    now = timezone.now()
    with transaction.atomic():
        events = list(
            OutboxEvent.objects.select_for_update(skip_locked=True).filter(
                published_at__isnull=True,
                attempts__lt=getattr(settings, 'OUTBOX_MAX_ATTEMPTS', 10),
            ).filter(
                Q(locked_until__isnull=True) | Q(locked_until__lte=now)
            ).order_by('created_at')[:batch_size]
        )
        if events:
            OutboxEvent.objects.filter(pk__in=[e.pk for e in events]).update(
                locked_until=now + timedelta(seconds=lease_seconds),
                attempts=F('attempts') + 1,
            )
    return events


def mark_published(event_id):
    OutboxEvent.objects.filter(pk=event_id, published_at__isnull=True).update(
        published_at=timezone.now()
    )


def mark_failed(event, exc):
    delay = min(2 ** event.attempts, 300)
    OutboxEvent.objects.filter(pk=event.pk).update(
        locked_until=timezone.now() + timedelta(seconds=delay),
        last_error=str(exc)[:500],
    )
    log.warning('outbox event %s failed (attempt %d): %s', event.id, event.attempts, exc)


def append(aggregate_type, aggregate_id, event_type, payload):
    """
    Write outbox event. MUST be inside atomic() that also commits the
    business-state change. Never call broker from here.
    """
    OutboxEvent.objects.create(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type=event_type,
        payload=payload,
    )
