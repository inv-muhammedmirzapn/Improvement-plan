"""Custom exceptions for Order Service."""


class OrderNotFound(Exception):
    pass


class InvalidStateTransition(Exception):
    def __init__(self, message, from_status=None, to_status=None):
        super().__init__(message)
        self.from_status = from_status
        self.to_status = to_status


class IdempotencyConflict(Exception):
    """Same idempotency key with a different request body."""
    pass


class OrderNotCancellable(Exception):
    pass


class TemporaryDatabaseError(Exception):
    pass


class BrokerTemporaryError(Exception):
    pass


class ServiceUnavailable(Exception):
    pass
