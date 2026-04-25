import pytest
from smolib import retry, T

no_wait = T.Wait.const(0)

async def ok_after(n: int, *, value=42):
    """Return Pending n-1 times, then Ok."""
    calls = 0
    async def fn():
        nonlocal calls; calls += 1
        return T.Ok(value) if calls >= n else T.Pending(f"attempt {calls}")
    return fn

async def err_after(n: int, *, error="fatal"):
    """Return Pending n-1 times, then Err."""
    calls = 0
    async def fn():
        nonlocal calls; calls += 1
        return T.Err(error) if calls >= n else T.Pending(f"attempt {calls}")
    return fn

# core loop

@pytest.mark.asyncio
async def test_success_first_attempt():
    result, attempts = await retry(await ok_after(1), n=3, wait=no_wait)
    assert result == T.Ok(42)
    assert attempts.k == 1
    assert attempts.reasons == ()

@pytest.mark.asyncio
async def test_success_after_retries():
    result, attempts = await retry(await ok_after(3), n=5, wait=no_wait)
    assert result == T.Ok(42)
    assert attempts.k == 3
    assert len(attempts.reasons) == 2

@pytest.mark.asyncio
async def test_exhaustion():
    result, attempts = await retry(await ok_after(99), n=3, wait=no_wait)
    assert result == T.Err(T.Exhausted())
    assert attempts.k == 3
    assert len(attempts.reasons) == 3

@pytest.mark.asyncio
async def test_err_stops_immediately():
    result, attempts = await retry(await err_after(1), n=5, wait=no_wait)
    assert result == T.Err("fatal")
    assert attempts.k == 1

@pytest.mark.asyncio
async def test_err_after_pending():
    result, attempts = await retry(await err_after(3), n=5, wait=no_wait)
    assert result == T.Err("fatal")
    assert attempts.k == 3
    assert len(attempts.reasons) == 2

@pytest.mark.asyncio
async def test_n_must_be_positive():
    with pytest.raises(ValueError):
        await retry(await ok_after(1), n=0, wait=no_wait)

# wait / timing

@pytest.mark.asyncio
async def test_wait_called_with_attempt_number():
    waits = []
    def record_wait(n): waits.append(n); return 0
    await retry(await ok_after(4), n=5, wait=record_wait)
    assert waits == [1, 2, 3]

@pytest.mark.asyncio
async def test_no_sleep_after_last_attempt():
    sleeps = []
    async def mock_sleep(t): sleeps.append(t)
    await retry(await ok_after(99), n=3, wait=no_wait, sleep=mock_sleep)
    assert len(sleeps) == 2  # not 3

@pytest.mark.asyncio
async def test_exp_backoff():
    w = T.Wait.exp(base=2.0, cap=60.0)
    assert w(1) == 2.0
    assert w(2) == 4.0
    assert w(10) == 60.0  # capped

@pytest.mark.asyncio
async def test_jitter_bounds():
    w = T.Wait.jitter(T.Wait.const(10))
    values = [w(1) for _ in range(200)]
    assert all(0 <= v <= 10 for v in values)

# metadata

@pytest.mark.asyncio
async def test_elapsed_tracked():
    tick = 0.0
    def clock(): return tick
    async def fn():
        nonlocal tick; tick += 1.0
        return T.Ok("done")
    result, attempts = await retry(fn, n=3, wait=no_wait, clock=clock)
    assert attempts.elapsed == 1.0

@pytest.mark.asyncio
async def test_reasons_collected():
    result, attempts = await retry(await ok_after(4), n=5, wait=no_wait)
    assert attempts.reasons == ("attempt 1", "attempt 2", "attempt 3")
