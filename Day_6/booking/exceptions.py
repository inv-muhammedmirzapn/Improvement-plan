class BookingError(Exception):
    pass


class EventNotFound(BookingError):
    pass


class EventNotOpen(BookingError):
    pass


class SeatsUnavailable(BookingError):
    def __init__(self, seat_ids=()):
        self.seat_ids = list(seat_ids)
        super().__init__(f"One or more seats are unavailable: {self.seat_ids}")


class IdempotencyConflict(BookingError):
    """Same idempotency key reused with a different request body."""
    pass


class PaymentNotFound(BookingError):
    pass


class TemporaryDatabaseError(Exception):
    """Deadlock / lock-wait-timeout / lost connection after retries. Safe for caller to retry."""
    pass


class GatewayTemporaryError(Exception):
    pass


class GatewayPermanentError(Exception):
    pass


# Alias for backwards compatibility with any camelCase variation
GateWayPermanentError = GatewayPermanentError


class BrokerTemporaryError(Exception):
    pass
