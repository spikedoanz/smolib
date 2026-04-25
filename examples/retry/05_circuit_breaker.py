"""Circuit breaker as a composable wrapper around any retryable operation."""
import random, time
from smolib import retry, t

class Breaker:
    """Trips open after `threshold` consecutive failures, resets after `cooldown` seconds."""
    def __init__(self, threshold: int = 3, cooldown: float = 5.0):
        self.threshold = threshold
        self.cooldown = cooldown
        self._failures = 0
        self._opened_at: float | None = None

    def is_open(self) -> bool:
        if self._opened_at is None: return False
        if time.monotonic() - self._opened_at > self.cooldown:
            self._opened_at = None
            self._failures = 0
            return False
        return True

    def record_success(self):
        self._failures = 0
        self._opened_at = None

    def record_failure(self):
        self._failures += 1
        if self._failures >= self.threshold:
            self._opened_at = time.monotonic()

def with_breaker(breaker: Breaker, op):
    """Wrap an operation so the breaker is consulted before each attempt."""
    def wrapped():
        if breaker.is_open():
            return t.Err("breaker open")
        result = op()
        match result:
            case t.Ok():    breaker.record_success()
            case t.Err():   breaker.record_failure()
            case t.Pending(): breaker.record_failure()
        return result
    return wrapped

# --- demo ---

def flaky_service() -> t.Attempt[str, str, str]:
    if random.random() < 0.4:
        return t.Pending("service unavailable")
    return t.Ok("response payload")

breaker = Breaker(threshold=5, cooldown=2.0)

for i in range(5):
    result, attempts = retry(
        with_breaker(breaker, flaky_service),
        n=6, wait=t.Wait.const(0.5),
    )
    match result:
        case t.Ok(value=v):
            print(f"  call {i}: ok after {attempts.k} attempts")
        case t.Err(error="breaker open"):
            print(f"  call {i}: breaker tripped, skipping")
        case t.Exhausted():
            print(f"  call {i}: exhausted ({attempts.reasons})")
        case t.Err(error=e):
            print(f"  call {i}: fatal: {e}")
