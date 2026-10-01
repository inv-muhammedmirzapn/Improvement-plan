"""
Outbox service for Restaurant Service.

Rules:
- claim_batch: SELECT FOR UPDATE SKIP LOCKED to avoid worker contention.
- mark_published: marks the event as published (idempotent if run twice).
- mark_failed: increments attempts, applies exponential back-off via locked_until.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import OutboxEvent

log = logging.getLogger(__name__)


def claim_batch():
    """Return a batch of unpublished events, acquiring a lease on each."""
    batch_size = getattr(settings, 'OUTBOX_BATCH_SIZE', 50)
    lease_seconds = getattr(settings, 'OUTBOX_LEASE_SECONDS', 60)
    now = timezone.now()

    with transaction.atomic():
        events = list(
            OutboxEvent.objects.select_for_update(skip_locked=True).filter(
                published_at__isnull=True,
                attempts__lt=getattr(settings, 'OUTBOX_MAX_ATTEMPTS', 10),
            ).filter(
                models_locked_until_filter(now)
            ).order_by('created_at')[:batch_size]
        )
        if events:
            OutboxEvent.objects.filter(pk__in=[e.pk for e in events]).update(
                locked_until=now + timedelta(seconds=lease_seconds),
                attempts=models_F_attempts(),
            )
    return events


def models_locked_until_filter(now):
    """Filter: locked_until is null OR locked_until <= now."""
    from django.db.models import Q
    return Q(locked_until__isnull=True) | Q(locked_until__lte=now)


def models_F_attempts():
    from django.db.models import F
    return F('attempts') + 1


def mark_published(event_id):
    """Mark event as published. Idempotent: safe to call twice."""
    OutboxEvent.objects.filter(pk=event_id, published_at__isnull=True).update(
        published_at=timezone.now()
    )


def mark_failed(event, exc):
    """Record failure and set back-off."""
    from django.db.models import F
    delay = min(2 ** event.attempts, 300)  # cap at 5 minutes
    OutboxEvent.objects.filter(pk=event.pk).update(
        locked_until=timezone.now() + timedelta(seconds=delay),
        last_error=str(exc)[:500],
    )
    log.warning('outbox event %s failed (attempt %d): %s', event.id, event.attempts, exc)


def append(aggregate_type, aggregate_id, event_type, payload, *, using_connection=None):
    """
    Write an outbox event. MUST be called inside an atomic() block that also
    commits the corresponding business-state change.
    Never publish to the broker inside this function.
    """
    OutboxEvent.objects.create(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type=event_type,
        payload=payload,
    )
