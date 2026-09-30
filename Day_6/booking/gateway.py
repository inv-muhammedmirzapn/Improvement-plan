import requests
from django.conf import settings
from .exceptions import GatewayPermanentError, GatewayTemporaryError


def create_payment(*, reference, amount, currency, idempotency_key):
    try:
        resp = requests.post(
            f"{settings.PAYMENT_GATEWAY_URL}/v1/payments",
            json={"reference": reference, "amount": str(amount), "currency": currency},
            headers={
                "Idempotency-Key": idempotency_key,
                "Authorization": f"Bearer {settings.PAYMENT_GATEWAY_API_KEY}",
            },
            timeout=(3.05, 10),
        )
    except (requests.Timeout, requests.ConnectionError) as exc:
        raise GatewayTemporaryError(str(exc)) from exc

    if resp.status_code >= 500 or resp.status_code in (408, 425, 429):
        raise GatewayTemporaryError(f"gateway {resp.status_code}")
    if resp.status_code >= 400:
        raise GatewayPermanentError(f"gateway {resp.status_code}: {resp.text[:200]}")
    return resp.json()