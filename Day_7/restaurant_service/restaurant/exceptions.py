"""Custom exceptions for Restaurant Service."""


class RestaurantNotFound(Exception):
    pass


class RestaurantClosed(Exception):
    pass


class MenuItemNotFound(Exception):
    pass


class MenuItemUnavailable(Exception):
    pass


class CapacityExceeded(Exception):
    """Restaurant has no remaining active-order slots."""
    pass


class InvalidStateTransition(Exception):
    pass


class IdempotencyConflict(Exception):
    """Same idempotency key, different request body."""
    pass


class TemporaryDatabaseError(Exception):
    """Transient DB error; caller should retry."""
    pass


class BrokerTemporaryError(Exception):
    """Transient broker error; outbox relay retries."""
    pass


class ServiceUnavailable(Exception):
    """Downstream service is unreachable."""
    pass
