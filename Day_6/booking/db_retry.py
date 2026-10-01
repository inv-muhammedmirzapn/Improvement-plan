"""Retry wrapper for transient PostgreSQL errors, applied to service entry points (outside atomic)."""
import functools
import logging
import random
import time

from django.db import InterfaceError, OperationalError, connection

from .exceptions import TemporaryDatabaseError

log = logging.getLogger(__name__)

# PostgreSQL transient SQLSTATE codes
# 40P01: deadlock_detected
# 40001: serialization_failure
# 55P03: lock_not_available
# 57014: query_canceled (e.g., statement_timeout / lock_timeout)
# 57P01: admin_shutdown
# 57P02: crash_shutdown
# 57P03: cannot_connect_now
# 08000: connection_exception
# 08003: connection_does_not_exist
# 08006: connection_failure
PG_RETRYABLE = {
    "40P01",
    "40001",
    "55P03",
    "57014",
    "57P01",
    "57P02",
    "57P03",
    "08000",
    "08003",
    "08006",
}
PG_DISCONNECT_CODES = {"57P01", "57P02", "57P03", "08000", "08003", "08006"}


def _is_retryable(exc):
    if isinstance(exc, InterfaceError):
        return True, True

    # Check PostgreSQL pgcode / sqlstate
    cause = getattr(exc, "__cause__", None) or exc
    pgcode = getattr(cause, "pgcode", None) or getattr(cause, "sqlstate", None)
    if pgcode and str(pgcode) in PG_RETRYABLE:
        should_reconnect = str(pgcode) in PG_DISCONNECT_CODES
        return True, should_reconnect

    msg = str(exc).lower()
    if "deadlock detected" in msg or "could not serialize access" in msg or "lock not available" in msg:
        return True, False

    return False, False


def retry_on_db_error(max_attempts=4, base_delay=0.05):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if connection.in_atomic_block:
                # Never retry inside someone else's transaction: the outer layer must retry.
                return fn(*args, **kwargs)
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except (OperationalError, InterfaceError) as exc:
                    retryable, should_reconnect = _is_retryable(exc)
                    if not retryable or attempt == max_attempts:
                        raise TemporaryDatabaseError(str(exc)) from exc #503
                    log.warning("db error in %s (attempt %d): %s, retrying", fn.__name__, attempt, exc)
                    if should_reconnect:
                        connection.close()  # force reconnect on next query
                    time.sleep(base_delay * (2 ** (attempt - 1)) * (0.5 + random.random()))
        return wrapper
    return decorator