"""Nested retry: inner loop for transient network errors, outer loop for transaction-level retries.

Inner retry handles quick blips (fast backoff, many attempts).
Outer retry handles "the whole operation needs to be re-driven" (slow backoff, few attempts).
"""
import random
from smolib import retry, t

def network_call() -> t.Attempt[str, str, dict]:
    r = random.random()
    if r < 0.4: return t.Pending("connection reset")
    if r < 0.5: return t.Err("malformed response")
    return t.Ok({"transaction_id": "tx_abc123"})

def do_transaction() -> t.Attempt[str, str, dict]:
    result, inner = retry(network_call, n=3, wait=t.Wait.const(0.2))
    match result:
        case t.Ok(value=v):
            if random.random() < 0.3:
                return t.Pending(f"transaction conflict after {inner.k} network calls")
            return t.Ok(v)
        case t.Exhausted():
            return t.Pending(f"network exhausted after {inner.k} tries: {inner.reasons}")
        case t.Err(error=e):
            return t.Err(e)

result, outer = retry(do_transaction, n=4, wait=t.Wait.exp(base=1.5, cap=10))
match result:
    case t.Ok(value=v):
        print(f"committed: {v}")
        print(f"  outer attempts: {outer.k}, elapsed: {outer.elapsed:.1f}s")
    case t.Exhausted():
        print(f"gave up after {outer.k} outer attempts")
        for i, reason in enumerate(outer.reasons, 1):
            print(f"  attempt {i}: {reason}")
    case t.Err(error=e):
        print(f"fatal: {e}")
