"""Transactional outbox: enqueue (inside business tx) + relay helpers (outside any tx)."""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import connection, transaction
from django.db.models import F, Q
from django.utils import timezone

from ..models import OutboxEvent

log = logging.getLogger(__name__)


def enqueue(*, aggregate_id, event_type, payload):
    """Call inside the SAME transaction.atomic() as the state change."""
    assert connection.in_atomic_block, "outbox.enqueue must run inside a transaction"
    return OutboxEvent.objects.get_or_create(
        aggregate_id=aggregate_id, event_type=event_type, defaults={"payload": payload}
    )


def claim_batch(batch_size=None):
    """Short tx: lock unpublished rows with SKIP LOCKED (disjoint batches per worker), stamp a
    lease, commit. Broker call happens AFTER this returns, holding no locks."""
    batch_size = batch_size or getattr(settings, "OUTBOX_BATCH_SIZE", 50)
    max_attempts = getattr(settings, "OUTBOX_MAX_ATTEMPTS", 10)
    lease_seconds = getattr(settings, "OUTBOX_LEASE_SECONDS", 60)
    now = timezone.now()
    with transaction.atomic():
        rows = list(
            OutboxEvent.objects.select_for_update(skip_locked=True)
            .filter(published_at__isnull=True, attempts__lt=max_attempts)
            .filter(Q(locked_until__isnull=True) | Q(locked_until__lte=now))
            .order_by("created_at")[:batch_size]
        )
        if rows:
            OutboxEvent.objects.filter(pk__in=[r.pk for r in rows]).update(
                locked_until=now + timedelta(seconds=lease_seconds),
                attempts=F("attempts") + 1,
            )
    return rows


def mark_published(event_id):
    OutboxEvent.objects.filter(pk=event_id, published_at__isnull=True).update(
        published_at=timezone.now(), last_error=""
    )


def mark_failed(event, error):
    backoff = min(5 * (2 ** event.attempts), 900)  # capped at 15 min
    OutboxEvent.objects.filter(pk=event.pk, published_at__isnull=True).update(
        locked_until=timezone.now() + timedelta(seconds=backoff), last_error=str(error)[:2000]
    )