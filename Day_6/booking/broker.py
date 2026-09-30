"""Message-broker / notification-platform publisher. NEVER call from inside transaction.atomic()."""
import requests
from django.conf import settings

from .exceptions import BrokerTemporaryError


def publish(*, message_id, event_type, aggregate_id, payload):
    try:
        resp = requests.post(
            settings.NOTIFICATION_BROKER_URL,
            json={"message_id": str(message_id), "type": event_type,
                  "aggregate_id": str(aggregate_id), "data": payload},
            headers={
                "Idempotency-Key": str(message_id),
                "X-Message-Id": str(message_id),
                "Authorization": f"Bearer {settings.NOTIFICATION_BROKER_TOKEN}",
            },
            timeout=(3.05, 10),
        )
    except (requests.Timeout, requests.ConnectionError) as exc:
        raise BrokerTemporaryError(str(exc)) from exc
    if resp.status_code >= 400:
        raise BrokerTemporaryError(f"broker {resp.status_code}")