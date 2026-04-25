"""Testing retry logic deterministically with injected clock and sleep.

No real time passes. No patching. No freezegun. Just functions.
"""
import asyncio
from smolib import retry, T

async def main():
    fake_time = 0.0
    sleeps: list[float] = []

    async def fake_sleep(d: float):
        nonlocal fake_time
        sleeps.append(d)
        fake_time += d

    call_count = 0
    async def op() -> T.Attempt[str, str, str]:
        nonlocal call_count; call_count += 1
        if call_count < 4: return T.Pending(f"try {call_count}")
        return T.Ok("done")

    result, attempts = await retry(
        op, n=5,
        wait=T.Wait.exp(base=2.0, cap=60.0),  # deterministic, no jitter
        sleep=fake_sleep,
        clock=lambda: fake_time,
    )

    assert result == T.Ok("done")
    assert attempts.k == 4
    assert attempts.reasons == ("try 1", "try 2", "try 3")
    assert sleeps == [2.0, 4.0, 8.0]  # exp backoff: 2^1, 2^2, 2^3
    assert attempts.elapsed == 14.0    # sum of sleeps
    print("all assertions passed")
    print(f"  sleeps: {sleeps}")
    print(f"  elapsed (fake): {attempts.elapsed}s")

if __name__ == "__main__":
    asyncio.run(main())
