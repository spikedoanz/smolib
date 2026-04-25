"""Zero-friction retry of an exception-throwing function.

`catch` adapts any function into the Attempt protocol
so you don't have to rewrite it. Caught exceptions become Pending
(retryable); uncaught exceptions propagate immediately.
"""
import random
from smolib import retry, catch, Ok, Exhausted, Wait

def flaky_read(path: str) -> str:
    """Existing function that throws — no smolib types needed."""
    if random.random() < 0.6:
        raise OSError("disk busy")
    return f"contents of {path}"

result, attempts = retry(
    catch(lambda: flaky_read("/tmp/data.txt"), on=OSError),
    n=5, wait=Wait.const(0.5),
)
match result:
    case Ok(value=v):
        print(f"read: {v} (after {attempts.k} tries)")
    case Exhausted():
        print(f"gave up after {attempts.k} tries: {attempts.reasons}")
