"""Handling server-directed Retry-After delays inside the operation.

The operation sleeps for the server's requested duration (clamped),
then returns Pending. Library backoff is disabled (wait=const(0))
so the server's timing is the only delay — no double-sleeping.
"""
import asyncio, random
from smolib import retry, t

MAX_SERVER_WAIT = 10.0  # never trust the server more than this

# simulated server that rate-limits for a while then responds
call_count = 0
async def fake_api() -> t.Attempt[str, str, dict]:
    global call_count; call_count += 1
    # first few calls get rate-limited with a Retry-After header
    if call_count <= 3:
        server_retry_after = random.uniform(0.5, 2.0)
        clamped = min(server_retry_after, MAX_SERVER_WAIT)
        print(f"    server said Retry-After: {server_retry_after:.1f}s (clamped to {clamped:.1f}s)")
        await asyncio.sleep(clamped)  # honor it locally, clamped
        return t.Pending(f"429 retry-after={server_retry_after:.1f}")
    return t.Ok({"data": "here"})

async def main():
    # const(0) disables library backoff — the op already waited
    result, attempts = await retry(fake_api, n=6, wait=t.Wait.const(0))
    match result:
        case t.Ok(value=v):
            print(f"got {v} after {attempts.k} attempts ({attempts.elapsed:.1f}s)")
            print(f"reasons: {attempts.reasons}")
        case t.Err(error=t.Exhausted()):
            print(f"gave up: {attempts.reasons}")

if __name__ == "__main__":
    asyncio.run(main())
