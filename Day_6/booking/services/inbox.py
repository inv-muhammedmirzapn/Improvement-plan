"""Consumer-side idempotency for at-least-once delivery."""
from django.db import IntegrityError, transaction

from ..models import ProcessedMessage


def process_once(message_id, consumer, handler):
    """Runs `handler` at most once per (message_id, consumer). Returns False for duplicates."""
    with transaction.atomic():
        try:
            with transaction.atomic():  # savepoint
                ProcessedMessage.objects.create(message_id=message_id, consumer=consumer)
        except IntegrityError:
            return False
        handler()
    return True