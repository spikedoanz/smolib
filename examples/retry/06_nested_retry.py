"""Nested retry: inner loop for transient network errors, outer loop for transaction-level retries.

Inner retry handles quick blips (fast backoff, many attempts).
Outer retry handles "the whole operation needs to be re-driven" (slow backoff, few attempts).
"""
import asyncio, random
from smolib import retry, t

async def network_call() -> t.Attempt[str, str, dict]:
    """Simulates a flaky network call."""
    r = random.random()
    if r < 0.4: return t.Pending("connection reset")
    if r < 0.5: return t.Err("malformed response")
    return t.Ok({"transaction_id": "tx_abc123"})

async def do_transaction() -> t.Attempt[str, str, dict]:
    """One transaction attempt = inner retry over network blips."""
    result, inner = await retry(network_call, n=3, wait=t.Wait.const(0.2))
    match result:
        case t.Ok(value=v):
            # simulate: 30% chance the transaction itself needs re-driving
            if random.random() < 0.3:
                return t.Pending(f"transaction conflict after {inner.k} network calls")
            return t.Ok(v)
        case t.Err(error=t.Exhausted()):
            return t.Pending(f"network exhausted after {inner.k} tries: {inner.reasons}")
        case t.Err(error=e):
            return t.Err(e)  # fatal network error, propagate up

async def main():
    result, outer = await retry(do_transaction, n=4, wait=t.Wait.exp(base=1.5, cap=10))
    match result:
        case t.Ok(value=v):
            print(f"committed: {v}")
            print(f"  outer attempts: {outer.k}, elapsed: {outer.elapsed:.1f}s")
        case t.Err(error=t.Exhausted()):
            print(f"gave up after {outer.k} outer attempts")
            for i, reason in enumerate(outer.reasons, 1):
                print(f"  attempt {i}: {reason}")
        case t.Err(error=e):
            print(f"fatal: {e}")

if __name__ == "__main__":
    asyncio.run(main())
