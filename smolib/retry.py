from typing import Awaitable, Callable
import asyncio
import time

from smolib.types import Ok, Err, Pending, Exhausted, Wait, Result, Attempt, Attempts


def catch(fn, on=Exception):
    """Caught exceptions become Pending (retryable). Uncaught propagate."""
    def wrapped():
        try: return Ok(fn())
        except on as e: return Pending(e)
    return wrapped


def acatch(fn, on=Exception):
    """Async version of catch."""
    async def wrapped():
        try: return Ok(await fn())
        except on as e: return Pending(e)
    return wrapped


def retry[R, E, T](
    fn      : Callable[[], Attempt[R, E, T]],
    n       : int,  # the children yearn for quantitative types
    wait    : Callable[[int], float]                = Wait.jitter(Wait.exp()),
    sleep   : Callable[[float], None]               = time.sleep,
    clock   : Callable[[], float]                   = time.monotonic,
) -> tuple[Result[E, T], Attempts[R]]:
    """
    Retry a potentially erroring | failing operation with backoff.

    ```
    from smolib import retry, Ok, Pending, Exhausted, Err

    def flaky() -> Ok[int] | Pending[str] | Err[str]:
        if random.random() < 0.5: return Pending("not ready")
        return Ok(42)

    result, attempts = retry(flaky, n=5)
    match result:
        case Ok(value=v):
            print(f"got {v} after {attempts.k} attempts in {attempts.elapsed:.1f}s")
        case Exhausted():
            print(f"gave up after {attempts.k} tries: {attempts.reasons}")
        case Err(error=e):
            print(f"fatal error: {e}")
    ```
    """
    if n < 1: raise ValueError("n must be >= 1")
    reasons: list[R] = []
    started: float = clock()
    def attempts(k: int) -> Attempts[R]:
        return Attempts(k=k, elapsed=clock() - started, reasons=tuple(reasons))
    for i in range(1, n + 1):
        result: Attempt[R, E, T] = fn()
        match result:
            case Ok(value=v):                        return Ok(v), attempts(i)
            case Err(error=e):                       return Err(e), attempts(i)
            case Pending(reason=r):
                reasons.append(r)
                if i == n: return Exhausted(), attempts(i)
                sleep(wait(i))
    raise RuntimeError("unreachable") # python's type checker can't prove this.


async def aretry[R, E, T](
    fn      : Callable[[], Awaitable[Attempt[R, E, T]]],
    n       : int,  # the children yearn for quantitative types
    wait    : Callable[[int], float]                = Wait.jitter(Wait.exp()),
    sleep   : Callable[[float], Awaitable[None]]    = asyncio.sleep,
    clock   : Callable[[], float]                   = time.monotonic,
) -> tuple[Result[E, T], Attempts[R]]:
    """Async version of retry."""
    if n < 1: raise ValueError("n must be >= 1")
    reasons: list[R] = []
    started: float = clock()
    def attempts(k: int) -> Attempts[R]:
        return Attempts(k=k, elapsed=clock() - started, reasons=tuple(reasons))
    for i in range(1, n + 1):
        result: Attempt[R, E, T] = await fn()
        match result:
            case Ok(value=v):                        return Ok(v), attempts(i)
            case Err(error=e):                       return Err(e), attempts(i)
            case Pending(reason=r):
                reasons.append(r)
                if i == n: return Exhausted(), attempts(i)
                await sleep(wait(i))
    raise RuntimeError("unreachable") # python's type checker can't prove this.
