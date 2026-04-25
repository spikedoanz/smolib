"""Testing retry logic deterministically with injected clock and sleep.

No real time passes. No patching. No freezegun. Just functions.
"""
from smolib import retry, t

fake_time = 0.0
sleeps: list[float] = []

def fake_sleep(d: float):
    global fake_time
    sleeps.append(d)
    fake_time += d

call_count = 0
def op() -> t.Attempt[str, str, str]:
    global call_count; call_count += 1
    if call_count < 4: return t.Pending(f"try {call_count}")
    return t.Ok("done")

result, attempts = retry(
    op, n=5,
    wait=t.Wait.exp(base=2.0, cap=60.0),  # deterministic, no jitter
    sleep=fake_sleep,
    clock=lambda: fake_time,
)

assert result == t.Ok("done")
assert attempts.k == 4
assert attempts.reasons == ("try 1", "try 2", "try 3")
assert sleeps == [2.0, 4.0, 8.0]  # exp backoff: 2^1, 2^2, 2^3
assert attempts.elapsed == 14.0    # sum of sleeps
print("all assertions passed")
print(f"  sleeps: {sleeps}")
print(f"  elapsed (fake): {attempts.elapsed}s")
