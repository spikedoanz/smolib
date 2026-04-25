"""Wall-clock deadline across the entire retry loop.

`with_deadline` wraps an operation so it returns Err once
the deadline has passed — no more attempts, regardless of
how many retries remain in the budget.

Handles the case where fn itself is slow: even if backoff
math says you have time, a 30-second operation can blow
past your budget.
"""
import random, time
from smolib import retry, Attempt, Ok, Pending, Err, Exhausted, Wait

def with_deadline(fn, seconds, clock=time.monotonic):
    """Stop retrying after `seconds` wall-clock time."""
    deadline = clock() + seconds
    def wrapped():
        if clock() >= deadline:
            return Err("deadline exceeded")
        return fn()
    return wrapped

# --- demo: fast operation, deadline bounds total wait ---

call_count = 0
def flaky_fast() -> Attempt[str, str, str]:
    global call_count; call_count += 1
    if random.random() < 0.7:
        return Pending(f"attempt {call_count}")
    return Ok("done")

print("--- fast operation, 5s deadline ---")
result, attempts = retry(
    with_deadline(flaky_fast, seconds=5),
    n=100,  # high budget, but deadline will cut it short
    wait=Wait.const(1),
)
match result:
    case Ok(value=v):
        print(f"  ok: {v} after {attempts.k} tries ({attempts.elapsed:.1f}s)")
    case Exhausted():
        print(f"  exhausted after {attempts.k} tries ({attempts.elapsed:.1f}s)")
    case Err(error=e):
        print(f"  stopped: {e} after {attempts.k} tries ({attempts.elapsed:.1f}s)")

# --- demo: slow operation that eats into the deadline ---

print("\n--- slow operation, 3s deadline ---")
def slow_op() -> Attempt[str, str, str]:
    time.sleep(1.5)  # simulates a slow call
    return Pending("still processing")

result, attempts = retry(
    with_deadline(slow_op, seconds=3),
    n=100,
    wait=Wait.const(0),  # no backoff — op itself is the bottleneck
)
match result:
    case Ok(value=v):
        print(f"  ok: {v}")
    case Exhausted():
        print(f"  exhausted after {attempts.k} tries ({attempts.elapsed:.1f}s)")
    case Err(error=e):
        print(f"  stopped: {e} after {attempts.k} tries ({attempts.elapsed:.1f}s)")
