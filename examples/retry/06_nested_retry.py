"""Nested retry: inner loop for transient network errors, outer loop for transaction-level retries.

Inner retry handles quick blips (fast backoff, many attempts).
Outer retry handles "the whole operation needs to be re-driven" (slow backoff, few attempts).
"""
import asyncio, random
from smolib import retry, T

async def network_call() -> T.Attempt[str, str, dict]:
    """Simulates a flaky network call."""
    r = random.random()
    if r < 0.4: return T.Pending("connection reset")
    if r < 0.5: return T.Err("malformed response")
    return T.Ok({"transaction_id": "tx_abc123"})

async def do_transaction() -> T.Attempt[str, str, dict]:
    """One transaction attempt = inner retry over network blips."""
    result, inner = await retry(network_call, n=3, wait=T.Wait.const(0.2))
    match result:
        case T.Ok(value=v):
            # simulate: 30% chance the transaction itself needs re-driving
            if random.random() < 0.3:
                return T.Pending(f"transaction conflict after {inner.k} network calls")
            return T.Ok(v)
        case T.Err(error=T.Exhausted()):
            return T.Pending(f"network exhausted after {inner.k} tries: {inner.reasons}")
        case T.Err(error=e):
            return T.Err(e)  # fatal network error, propagate up

async def main():
    result, outer = await retry(do_transaction, n=4, wait=T.Wait.exp(base=1.5, cap=10))
    match result:
        case T.Ok(value=v):
            print(f"committed: {v}")
            print(f"  outer attempts: {outer.k}, elapsed: {outer.elapsed:.1f}s")
        case T.Err(error=T.Exhausted()):
            print(f"gave up after {outer.k} outer attempts")
            for i, reason in enumerate(outer.reasons, 1):
                print(f"  attempt {i}: {reason}")
        case T.Err(error=e):
            print(f"fatal: {e}")

if __name__ == "__main__":
    asyncio.run(main())
