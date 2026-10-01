"""
Inbox service: consumer-side idempotency using ProcessedMessage table.
"""
import logging

from django.db import IntegrityError, transaction

from ..models import ProcessedMessage

log = logging.getLogger(__name__)


def process_once(message_id, consumer, handler):
    """
    Execute handler exactly once for a given (message_id, consumer) pair.
    Safe for duplicate event delivery.
    Returns True if handler was executed, False if already processed.
    """
    try:
        with transaction.atomic():
            ProcessedMessage.objects.create(message_id=message_id, consumer=consumer)
            result = handler()
            return result
    except IntegrityError:
        log.info('duplicate message %s for consumer %s — skipping', message_id, consumer)
        return None
