"""Inbox service for Order Service — same pattern as Restaurant Service."""
import logging
from django.db import IntegrityError, transaction
from ..models import ProcessedMessage

log = logging.getLogger(__name__)


def process_once(message_id, consumer, handler):
    try:
        with transaction.atomic():
            ProcessedMessage.objects.create(message_id=message_id, consumer=consumer)
            return handler()
    except IntegrityError:
        log.info('duplicate message %s for consumer %s — skipping', message_id, consumer)
        return None
