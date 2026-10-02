"""
retry.py — Generic exponential backoff retry policy.

Single source of truth for "which failures are worth retrying" and "how
long to wait". 

Retried: 408, 429, 500, 502, 503, 504, connection resets and timeouts.
Not retried: every other 4xx, because a bad token or a rejected parameter
will not fix itself.
"""
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

log = logging.getLogger("pompom_meta.retry")

RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})


@dataclass
class RetryPolicy:
    """Exponential backoff schedule: 2s, 4s, 8s, 16s by default."""

    max_attempts: int = 5
    initial_delay: float = 2.0
    multiplier: float = 2.0
    max_delay: float = 32.0

    def delay_for(self, attempt: int) -> float:
        """Delay before retry number `attempt` (1-based)."""
        return min(self.initial_delay * (self.multiplier ** (attempt - 1)),
                   self.max_delay)

    @property
    def max_retries(self) -> int:
        return max(0, self.max_attempts - 1)


def is_retryable_status(status: int) -> bool:
    return status in RETRYABLE_STATUS


def retry_call(operation: Callable[[], object], *,
               policy: RetryPolicy | None = None,
               should_retry: Callable[[BaseException], bool] | None = None,
               label: str = "operation"):
    """Call `operation`, retrying transient failures with backoff.

    Args:
        operation: zero argument callable to run.
        policy: backoff schedule; a default policy is used when omitted.
        should_retry: predicate deciding whether an exception is transient.
            When omitted nothing is retried.
        label: name used in log lines.

    Returns:
        Whatever `operation` returns.

    Raises:
        The last exception raised by `operation`.
    """
    active = policy or RetryPolicy()
    predicate = should_retry or (lambda _exc: False)

    for attempt in range(1, active.max_attempts + 1):
        try:
            return operation()
        except BaseException as exc:  # noqa: BLE001 - re-raised below
            if attempt >= active.max_attempts or not predicate(exc):
                raise
            wait = active.delay_for(attempt)
            log.warning("%s failed (%s) — retry %s/%s in %.0fs",
                        label, exc, attempt, active.max_retries, wait)
            time.sleep(wait)

    raise RuntimeError(f"{label} exhausted its retry budget")  # pragma: no cover
