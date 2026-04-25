"""Handling server-directed Retry-After delays inside the operation.

The operation sleeps for the server's requested duration (clamped),
then returns Pending. Library backoff is disabled (wait=const(0))
so the server's timing is the only delay — no double-sleeping.
"""
import random, time
from smolib import retry, t

MAX_SERVER_WAIT = 10.0  # never trust the server more than this

call_count = 0
def fake_api() -> t.Attempt[str, str, dict]:
    global call_count; call_count += 1
    if call_count <= 3:
        server_retry_after = random.uniform(0.5, 2.0)
        clamped = min(server_retry_after, MAX_SERVER_WAIT)
        print(f"    server said Retry-After: {server_retry_after:.1f}s (clamped to {clamped:.1f}s)")
        time.sleep(clamped)
        return t.Pending(f"429 retry-after={server_retry_after:.1f}")
    return t.Ok({"data": "here"})

result, attempts = retry(fake_api, n=6, wait=t.Wait.const(0))
match result:
    case t.Ok(value=v):
        print(f"got {v} after {attempts.k} attempts ({attempts.elapsed:.1f}s)")
        print(f"reasons: {attempts.reasons}")
    case t.Exhausted():
        print(f"gave up: {attempts.reasons}")
