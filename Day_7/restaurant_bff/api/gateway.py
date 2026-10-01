"""
HTTP gateway for Restaurant BFF.
Same retry/timeout pattern as Customer BFF gateway.
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


class ServiceForbidden(ServiceError):
    def __init__(self, message):
        super().__init__(message, status_code=403)


def _call(method, url, *, timeout, retries=2, backoff=0.5, headers=None, **kwargs):
    last_exc = None
    for attempt in range(1, retries + 2):
        try:
            resp = requests.request(method, url, timeout=timeout, headers=headers or {}, **kwargs)
            if resp.status_code >= 500:
                log.warning('%s %s → %d (attempt %d)', method, url, resp.status_code, attempt)
                if attempt <= retries:
                    time.sleep(backoff * (2 ** (attempt - 1)))
                    continue
                raise ServiceUnavailable(f'Upstream service unavailable: {url}', status_code=resp.status_code)
            return resp
        except requests.exceptions.Timeout:
            last_exc = ServiceUnavailable(f'Timeout: {url}')
        except requests.exceptions.ConnectionError as exc:
            last_exc = ServiceUnavailable(f'Connection error: {url}')
        if attempt <= retries:
            time.sleep(backoff * (2 ** (attempt - 1)))
    raise last_exc


def _rs_url(path=''):
    base = getattr(settings, 'RESTAURANT_SERVICE_URL', 'http://127.0.0.1:8001')
    return f'{base.rstrip("/")}/{path.lstrip("/")}'


def _os_url(path=''):
    base = getattr(settings, 'ORDER_SERVICE_URL', 'http://127.0.0.1:8002')
    return f'{base.rstrip("/")}/{path.lstrip("/")}'


def _rt():
    return getattr(settings, 'RESTAURANT_SERVICE_TIMEOUT', 5)


def _ot():
    return getattr(settings, 'ORDER_SERVICE_TIMEOUT', 5)


def _r():
    return getattr(settings, 'SERVICE_MAX_RETRIES', 2)


def _restaurant_headers(restaurant_id):
    return {'X-Restaurant-ID': str(restaurant_id)}


# ── Menu management ────────────────────────────────────────────────────────────

def create_menu_item(restaurant_id, name, description, price):
    resp = _call(
        'POST',
        _rs_url(f'restaurants/{restaurant_id}/menu/add/'),
        json={'name': name, 'description': description, 'price': str(price)},
        headers=_restaurant_headers(restaurant_id),
        timeout=_rt(), retries=_r(),
    )
    if resp.status_code == 404:
        raise ServiceNotFound(resp.json().get('detail', 'Not found.'))
    return resp.json()


def update_menu_item(restaurant_id, item_id, **fields):
    resp = _call(
        'PATCH',
        _rs_url(f'restaurants/{restaurant_id}/menu/{item_id}/'),
        json=fields,
        headers=_restaurant_headers(restaurant_id),
        timeout=_rt(), retries=_r(),
    )
    if resp.status_code == 404:
        raise ServiceNotFound(resp.json().get('detail', 'Not found.'))
    if resp.status_code == 403:
        raise ServiceForbidden(resp.json().get('detail', 'Forbidden.'))
    return resp.json()


def set_item_availability(restaurant_id, item_id, is_available):
    resp = _call(
        'POST',
        _rs_url(f'restaurants/{restaurant_id}/menu/{item_id}/availability/'),
        json={'is_available': is_available},
        headers=_restaurant_headers(restaurant_id),
        timeout=_rt(), retries=_r(),
    )
    if resp.status_code == 404:
        raise ServiceNotFound(resp.json().get('detail', 'Not found.'))
    return resp.json()


def close_restaurant(restaurant_id):
    resp = _call(
        'POST',
        _rs_url(f'restaurants/{restaurant_id}/close/'),
        headers=_restaurant_headers(restaurant_id),
        timeout=_rt(), retries=_r(),
    )
    if resp.status_code == 404:
        raise ServiceNotFound(resp.json().get('detail', 'Not found.'))
    return resp.json()


# ── Order management ───────────────────────────────────────────────────────────

def get_restaurant_orders(restaurant_id, status_filter=None):
    params = {}
    if status_filter:
        params['status'] = status_filter
    resp = _call(
        'GET',
        _os_url(f'restaurants/{restaurant_id}/orders/'),
        params=params,
        headers=_restaurant_headers(restaurant_id),
        timeout=_ot(), retries=_r(),
    )
    return resp.json()


def accept_order(restaurant_id, order_id):
    resp = _call(
        'POST',
        _os_url(f'orders/{order_id}/accept/'),
        headers=_restaurant_headers(restaurant_id),
        timeout=_ot(), retries=0,
    )
    if resp.status_code == 404:
        raise ServiceNotFound(resp.json().get('detail', 'Not found.'))
    if resp.status_code == 409:
        raise ServiceConflict(resp.json().get('detail', 'Conflict.'))
    return resp.json()


def reject_order(restaurant_id, order_id):
    resp = _call(
        'POST',
        _os_url(f'orders/{order_id}/reject/'),
        headers=_restaurant_headers(restaurant_id),
        timeout=_ot(), retries=0,
    )
    if resp.status_code == 404:
        raise ServiceNotFound(resp.json().get('detail', 'Not found.'))
    if resp.status_code == 409:
        raise ServiceConflict(resp.json().get('detail', 'Conflict.'))
    return resp.json()


def start_preparing(restaurant_id, order_id):
    resp = _call(
        'POST',
        _os_url(f'orders/{order_id}/preparing/'),
        headers=_restaurant_headers(restaurant_id),
        timeout=_ot(), retries=0,
    )
    if resp.status_code == 404:
        raise ServiceNotFound(resp.json().get('detail', 'Not found.'))
    if resp.status_code == 409:
        raise ServiceConflict(resp.json().get('detail', 'Conflict.'))
    return resp.json()


def mark_ready(restaurant_id, order_id):
    resp = _call(
        'POST',
        _os_url(f'orders/{order_id}/ready/'),
        headers=_restaurant_headers(restaurant_id),
        timeout=_ot(), retries=0,
    )
    if resp.status_code == 404:
        raise ServiceNotFound(resp.json().get('detail', 'Not found.'))
    if resp.status_code == 409:
        raise ServiceConflict(resp.json().get('detail', 'Conflict.'))
    return resp.json()
