"""Nested retry: inner loop for transient network errors, outer loop for transaction-level retries.

Inner retry handles quick blips (fast backoff, many attempts).
Outer retry handles "the whole operation needs to be re-driven" (slow backoff, few attempts).
"""
import random
from smolib import retry, Attempt, Ok, Pending, Err, Exhausted, Wait

def network_call() -> Attempt[str, str, dict]:
    r = random.random()
    if r < 0.4: return Pending("connection reset")
    if r < 0.5: return Err("malformed response")
    return Ok({"transaction_id": "tx_abc123"})

def do_transaction() -> Attempt[str, str, dict]:
    result, inner = retry(network_call, n=3, wait=Wait.const(0.2))
    match result:
        case Ok(value=v):
            if random.random() < 0.3:
                return Pending(f"transaction conflict after {inner.k} network calls")
            return Ok(v)
        case Exhausted():
            return Pending(f"network exhausted after {inner.k} tries: {inner.reasons}")
        case Err(error=e):
            return Err(e)

result, outer = retry(do_transaction, n=4, wait=Wait.exp(base=1.5, cap=10))
match result:
    case Ok(value=v):
        print(f"committed: {v}")
        print(f"  outer attempts: {outer.k}, elapsed: {outer.elapsed:.1f}s")
    case Exhausted():
        print(f"gave up after {outer.k} outer attempts")
        for i, reason in enumerate(outer.reasons, 1):
            print(f"  attempt {i}: {reason}")
    case Err(error=e):
        print(f"fatal: {e}")
