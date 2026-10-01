"""
Broker stub for Restaurant Service.
In production this would publish to Redis Streams / RabbitMQ / Kafka.
For this implementation it logs the event (or can be swapped for a real publisher).
"""
import json
import logging

log = logging.getLogger(__name__)


def publish(message_id, event_type, aggregate_id, payload):
    """
    Publish a message to the event broker.
    Called by the outbox relay OUTSIDE of any database transaction.
    """
    message = {
        'message_id': str(message_id),
        'event_type': event_type,
        'aggregate_id': str(aggregate_id),
        'data': payload,
    }
    log.info('[BROKER] publishing %s: %s', event_type, json.dumps(message))
    # TODO: replace with real broker publish (redis streams, rabbitmq, etc.)
    return True
