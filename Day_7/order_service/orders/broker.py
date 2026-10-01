"""Broker stub for Order Service."""
import json
import logging

log = logging.getLogger(__name__)


def publish(message_id, event_type, aggregate_id, payload):
    message = {
        'message_id': str(message_id),
        'event_type': event_type,
        'aggregate_id': str(aggregate_id),
        'data': payload,
    }
    log.info('[BROKER] publishing %s: %s', event_type, json.dumps(message))
    return True
