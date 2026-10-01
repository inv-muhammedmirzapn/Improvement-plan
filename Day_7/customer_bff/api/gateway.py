"""
HTTP gateway for Customer BFF.

Implements per-service timeouts, retry with exponential backoff,
and partial-failure handling. Never exposes raw internal service responses.
"""
import logging
import time

import requests
from django.conf import settings

log = logging.getLogger(__name__)


class ServiceError(Exception):
    def __init__(self, message, status_code=503, detail=None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail or message


class ServiceUnavailable(ServiceError):
    pass


class ServiceNotFound(ServiceError):
    def __init__(self, message):
        super().__init__(message, status_code=404)


class ServiceConflict(ServiceError):
    def __init__(self, message, detail=None):
        super().__init__(message, status_code=409, detail=detail)


class ServiceValidationError(ServiceError):
    def __init__(self, message, detail=None):
        super().__init__(message, status_code=422, detail=detail)


def _call(method, url, *, timeout, retries=2, backoff=0.5, **kwargs):
    """
    Make an HTTP call with retry and exponential backoff.
    Retries only on 5xx and connection errors (transient failures).
    Does NOT retry on 4xx (client errors).
    """
    last_exc = None
    for attempt in range(1, retries + 2):
        try:
            resp = requests.request(method, url, timeout=timeout, **kwargs)
            if resp.status_code >= 500:
                log.warning('%s %s returned %d (attempt %d)', method, url, resp.status_code, attempt)
                if attempt <= retries:
                    time.sleep(backoff * (2 ** (attempt - 1)))
                    continue
                raise ServiceUnavailable(
                    f'Upstream service unavailable: {url}',
                    status_code=resp.status_code,
                )
            return resp
        except requests.exceptions.Timeout:
            log.warning('%s %s timed out (attempt %d)', method, url, attempt)
            last_exc = ServiceUnavailable(f'Upstream service timed out: {url}')
        except requests.exceptions.ConnectionError as exc:
            log.warning('%s %s connection error (attempt %d): %s', method, url, attempt, exc)
            last_exc = ServiceUnavailable(f'Cannot connect to upstream: {url}')
        if attempt <= retries:
            time.sleep(backoff * (2 ** (attempt - 1)))
    raise last_exc


def _restaurant_url(path=''):
    base = getattr(settings, 'RESTAURANT_SERVICE_URL', 'http://127.0.0.1:8001')
    return f'{base.rstrip("/")}/{path.lstrip("/")}'


def _order_url(path=''):
    base = getattr(settings, 'ORDER_SERVICE_URL', 'http://127.0.0.1:8002')
    return f'{base.rstrip("/")}/{path.lstrip("/")}'


def _rt():
    return getattr(settings, 'RESTAURANT_SERVICE_TIMEOUT', 5)


def _ot():
    return getattr(settings, 'ORDER_SERVICE_TIMEOUT', 5)


def _retries():
    return getattr(settings, 'SERVICE_MAX_RETRIES', 2)


# ── Restaurant Service calls ───────────────────────────────────────────────────

def get_restaurants():
    resp = _call('GET', _restaurant_url('restaurants/'), timeout=_rt(), retries=_retries())
    return resp.json()


def get_restaurant(restaurant_id):
    resp = _call('GET', _restaurant_url(f'restaurants/{restaurant_id}/'), timeout=_rt(), retries=_retries())
    if resp.status_code == 404:
        raise ServiceNotFound(f'Restaurant {restaurant_id} not found.')
    return resp.json()


def get_menu(restaurant_id):
    resp = _call('GET', _restaurant_url(f'restaurants/{restaurant_id}/menu/'),
                 timeout=_rt(), retries=_retries())
    if resp.status_code == 404:
        raise ServiceNotFound(f'Restaurant {restaurant_id} not found.')
    return resp.json()


def validate_order_items(restaurant_id, item_ids):
    """Synchronous validation before creating an order."""
    resp = _call(
        'POST',
        _restaurant_url(f'internal/restaurants/{restaurant_id}/validate-items/'),
        json={'item_ids': [str(i) for i in item_ids]},
        timeout=_rt(),
        retries=_retries(),
    )
    if resp.status_code == 404:
        raise ServiceNotFound(resp.json().get('detail', 'Not found.'))
    if resp.status_code == 409:
        raise ServiceConflict(resp.json().get('detail', 'Conflict.'))
    return resp.json()['items']


def reserve_capacity(restaurant_id):
    resp = _call(
        'POST',
        _restaurant_url(f'internal/restaurants/{restaurant_id}/reserve-capacity/'),
        timeout=_rt(),
        retries=0,  # capacity reservation must not be retried blindly
    )
    if resp.status_code == 409:
        raise ServiceConflict(resp.json().get('detail', 'Restaurant is closed.'))
    if resp.status_code == 429:
        raise ServiceConflict(resp.json().get('detail', 'Capacity exceeded.'), detail='CAPACITY_EXCEEDED')
    return resp.json()


def release_capacity(restaurant_id):
    """Fire-and-forget; called in cleanup paths."""
    try:
        _call(
            'POST',
            _restaurant_url(f'internal/restaurants/{restaurant_id}/release-capacity/'),
            timeout=_rt(),
            retries=_retries(),
        )
    except ServiceUnavailable:
        log.warning('release_capacity failed for restaurant %s — outbox reconciliation will fix', restaurant_id)


# ── Order Service calls ────────────────────────────────────────────────────────

def create_order(customer_id, restaurant_id, restaurant_name, idempotency_key, items):
    resp = _call(
        'POST',
        _order_url('orders/'),
        json={
            'restaurant_id': str(restaurant_id),
            'restaurant_name': restaurant_name,
            'idempotency_key': idempotency_key,
            'items': items,
        },
        headers={'X-Customer-ID': str(customer_id)},
        timeout=_ot(),
        retries=0,  # idempotency key makes this safe to retry at the app level
    )
    if resp.status_code == 422:
        raise ServiceValidationError(resp.json().get('detail', 'Idempotency conflict.'))
    return resp.json(), resp.status_code == 201


def get_order(order_id, customer_id):
    resp = _call(
        'GET',
        _order_url(f'orders/{order_id}/'),
        headers={'X-Customer-ID': str(customer_id)},
        timeout=_ot(),
        retries=_retries(),
    )
    if resp.status_code == 404:
        raise ServiceNotFound(f'Order {order_id} not found.')
    return resp.json()


def cancel_order(order_id, customer_id):
    resp = _call(
        'POST',
        _order_url(f'orders/{order_id}/cancel/'),
        headers={'X-Customer-ID': str(customer_id)},
        timeout=_ot(),
        retries=0,
    )
    if resp.status_code == 404:
        raise ServiceNotFound(f'Order {order_id} not found.')
    if resp.status_code == 409:
        raise ServiceConflict(resp.json().get('detail', 'Order cannot be cancelled.'))
    return resp.json()
