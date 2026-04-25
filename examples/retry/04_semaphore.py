"""Bounded concurrency with retry: semaphore inside the operation.

The permit is held only during the actual call, not during backoff sleep.
This means other coroutines can use the permit while we're backing off.
"""
import asyncio, random
from smolib import aretry, Attempt, Ok, Pending, Wait

sem = asyncio.Semaphore(2)  # max 2 concurrent in-flight calls

async def fetch(url: str) -> Attempt[str, str, str]:
    async with sem:
        # simulate a flaky network call
        await asyncio.sleep(random.uniform(0.1, 0.3))
        if random.random() < 0.5:
            return Pending(f"timeout on {url}")
        return Ok(f"body of {url}")

async def fetch_with_retry(url: str):
    result, attempts = await aretry(lambda: fetch(url), n=5, wait=Wait.const(0.5))
    match result:
        case Ok(value=body):
            print(f"  {url}: ok after {attempts.k} tries ({attempts.elapsed:.1f}s)")
        case _:
            print(f"  {url}: failed after {attempts.k} tries")

async def main():
    urls = [f"https://example.com/page/{i}" for i in range(6)]
    await asyncio.gather(*(fetch_with_retry(u) for u in urls))

if __name__ == "__main__":
    asyncio.run(main())
