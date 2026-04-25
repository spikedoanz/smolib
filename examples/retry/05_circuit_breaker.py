"""Circuit breaker as a composable wrapper around any retryable operation."""
import asyncio, random, time
from smolib import retry, T

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
    async def wrapped():
        if breaker.is_open():
            return T.Err("breaker open")  # fatal — don't waste retry budget
        result = await op()
        match result:
            case T.Ok():    breaker.record_success()
            case T.Err():   breaker.record_failure()
            case T.Pending(): breaker.record_failure()
        return result
    return wrapped

# --- demo ---

async def flaky_service() -> T.Attempt[str, str, str]:
    if random.random() < 0.4:
        return T.Pending("service unavailable")
    return T.Ok("response payload")

async def main():
    breaker = Breaker(threshold=5, cooldown=2.0)

    for i in range(5):
        result, attempts = await retry(
            with_breaker(breaker, flaky_service),
            n=6, wait=T.Wait.const(0.5),
        )
        match result:
            case T.Ok(value=v):
                print(f"  call {i}: ok after {attempts.k} attempts")
            case T.Err(error="breaker open"):
                print(f"  call {i}: breaker tripped, skipping")
            case T.Err(error=T.Exhausted()):
                print(f"  call {i}: exhausted ({attempts.reasons})")
            case T.Err(error=e):
                print(f"  call {i}: fatal: {e}")

if __name__ == "__main__":
    asyncio.run(main())
