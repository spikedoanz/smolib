from typing import Awaitable, Callable
import asyncio
import time

from smolib.types import Ok, Err, Pending, Exhausted, Wait, Result, Attempt, Attempts


async def retry[R, E, T](
    fn      : Callable[[], Awaitable[Attempt[R, E, T]]],
    n       : int,  # the children yearn for quantitative types
    wait    : Callable[[int], float]                = Wait.jitter(Wait.exp()),
    sleep   : Callable[[float], Awaitable[None]]    = asyncio.sleep,
    clock   : Callable[[], float]                   = time.monotonic,
) -> tuple[Result[E | Exhausted, T], Attempts[R]]:
    """
    Retry a potentially erroring | failing operation with backoff.

    ```
    from smolib import retry, t

    async def flaky() -> t.Attempt[str, str, int]:
        if random.random() < 0.5: return t.Pending("not ready")
        return t.Ok(42)

    result, attempts = await retry(flaky, n=5)
    match result:
        case t.Ok(value=v):
            print(f"got {v} after {attempts.k} attempts in {attempts.elapsed:.1f}s")
        case t.Err(error=t.Exhausted()):
            print(f"gave up after {attempts.k} tries: {attempts.reasons}")
        case t.Err(error=e):
            print(f"fatal error: {e}")
    ```
    """
    if n < 1: raise ValueError("n must be >= 1")
    reasons: list[R] = []
    started: float = clock()
    for i in range(1, n + 1):
        result: Attempt[R, E, T] = await fn()
        # Called immediately -- closing over mutable `reasons` is safe.
        def attemptor() -> Attempts[R]:
            return Attempts(k=i, elapsed=clock() - started, reasons=tuple(reasons))
        match result:
            case Ok(value=v):                        return Ok(v), attemptor()
            case Err(error=e):                       return Err(e), attemptor()
            case Pending(reason=r):
                reasons.append(r)
                if i == n: return Err(Exhausted()), attemptor()
                await sleep(wait(i))
    raise RuntimeError("unreachable") # python's type checker can't prove this.
