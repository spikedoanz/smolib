"""Solving backwards: compute n from a deadline and a wait strategy.

When your wait strategy is deterministic, you can compute the
worst-case sleep budget upfront and pick n to fit your deadline.
The bound is known at construction time, not discovered at runtime.
"""
from smolib import Wait

def max_n_for_deadline(deadline: float, wait: callable) -> int:
    """How many attempts fit in `deadline` seconds of sleep time?"""
    total = 0.0
    n = 0
    while True:
        n += 1
        # sleep happens after attempts 1..n-1 (not after the last)
        if n > 1:
            total += wait(n - 1)
        if total > deadline:
            return n - 1
    return n

# --- examples ---

exp = Wait.exp(base=2.0, cap=60.0)
const = Wait.const(5.0)
linear = Wait.linear(3.0)

for name, wait, deadline in [
    ("exp(2, cap=60)", exp, 30),
    ("exp(2, cap=60)", exp, 120),
    ("const(5)",       const, 30),
    ("linear(3)",      linear, 30),
]:
    n = max_n_for_deadline(deadline, wait)
    sleeps = [wait(i) for i in range(1, n)]
    total_sleep = sum(sleeps)
    print(f"  {name}, deadline={deadline}s -> n={n}, total_sleep={total_sleep:.1f}s")
    print(f"    sleeps: {[f'{s:.1f}' for s in sleeps]}")
