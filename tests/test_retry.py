import pytest

from smolib import t, retry

P, O, E, X = t.Pending, t.Ok, t.Err, t.Exhausted


def scripted(outcomes):
    calls = []

    async def fn():
        i = len(calls)
        calls.append(i + 1)
        assert i < len(outcomes), "retry called fn after terminal outcome"
        return outcomes[i]

    return fn, calls


def record_wait_sleep(multiplier=10.0):
    waits, sleeps = [], []

    def wait(i):
        waits.append(i)
        return i * multiplier

    async def sleep(seconds):
        sleeps.append(seconds)

    return wait, sleep, waits, sleeps


def clock_advances_on_sleep():
    elapsed = 0.0
    sleeps = []

    def clock():
        return elapsed

    async def sleep(seconds):
        nonlocal elapsed
        sleeps.append(seconds)
        elapsed += seconds

    return clock, sleep, sleeps


RETRY_CASES = [
    pytest.param([O(42)], 3, O(42), 1, (), [], [], id="ok-first"),
    pytest.param(
        [P("attempt 1"), P("attempt 2"), O(42)],
        5,
        O(42),
        3,
        ("attempt 1", "attempt 2"),
        [1, 2],
        [10.0, 20.0],
        id="ok-after-pending",
    ),
    pytest.param([E("fatal")], 5, E("fatal"), 1, (), [], [], id="err-first"),
    pytest.param(
        [P("attempt 1"), P("attempt 2"), E("fatal")],
        5,
        E("fatal"),
        3,
        ("attempt 1", "attempt 2"),
        [1, 2],
        [10.0, 20.0],
        id="err-after-pending",
    ),
    pytest.param(
        [P("attempt 1"), P("attempt 2"), P("attempt 3")],
        3,
        E(X()),
        3,
        ("attempt 1", "attempt 2", "attempt 3"),
        [1, 2],
        [10.0, 20.0],
        id="exhausted",
    ),
]


@pytest.mark.parametrize(
    "outcomes,n,expected,k,reasons,expected_waits,expected_sleeps",
    RETRY_CASES,
)
@pytest.mark.asyncio
async def test_retry_state_machine(
    outcomes, n, expected, k, reasons, expected_waits, expected_sleeps
):
    fn, fn_calls = scripted(outcomes)
    wait, sleep, waits, sleeps = record_wait_sleep()

    result, attempts = await retry(fn, n=n, wait=wait, sleep=sleep)

    assert result == expected
    assert attempts.k == k
    assert attempts.reasons == reasons
    assert fn_calls == list(range(1, k + 1))
    assert waits == expected_waits
    assert sleeps == expected_sleeps


@pytest.mark.parametrize("n", [0, -1])
@pytest.mark.asyncio
async def test_invalid_n_validates_before_side_effects(n):
    def fail_sync(*_):
        raise AssertionError("sync side effect should not run")

    async def fail_async(*_):
        raise AssertionError("async side effect should not run")

    with pytest.raises(ValueError, match="n must be >= 1"):
        await retry(fail_async, n=n, wait=fail_sync, sleep=fail_async, clock=fail_sync)


def test_exp_backoff_caps_values():
    wait = t.Wait.exp(base=2.0, cap=60.0)
    assert [wait(1), wait(2), wait(10)] == [2.0, 4.0, 60.0]


def test_jitter_bounds():
    wait = t.Wait.jitter(t.Wait.const(10))
    assert all(0 <= wait(1) <= 10 for _ in range(200))


ELAPSED_CASES = [
    pytest.param([P("pending"), O("done")], 3, t.Wait.const(2.5), O("done"), [2.5], id="ok"),
    pytest.param([P("pending"), E("fatal")], 3, t.Wait.const(4.0), E("fatal"), [4.0], id="err"),
    pytest.param(
        [P("attempt 1"), P("attempt 2"), P("attempt 3")],
        3,
        lambda i: float(i),
        E(X()),
        [1.0, 2.0],
        id="exhausted",
    ),
]


@pytest.mark.parametrize("outcomes,n,wait,expected,expected_sleeps", ELAPSED_CASES)
@pytest.mark.asyncio
async def test_elapsed_tracks_time_spent_sleeping(
    outcomes, n, wait, expected, expected_sleeps
):
    fn, _ = scripted(outcomes)
    clock, sleep, sleeps = clock_advances_on_sleep()

    result, attempts = await retry(fn, n=n, wait=wait, sleep=sleep, clock=clock)

    assert result == expected
    assert sleeps == expected_sleeps
    assert attempts.elapsed == sum(expected_sleeps)
