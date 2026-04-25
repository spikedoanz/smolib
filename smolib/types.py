from dataclasses import dataclass
from random import Random
from typing import Callable

@dataclass(frozen=True)
class Ok[T]: value: T

@dataclass(frozen=True)
class Err[E]: error: E

@dataclass(frozen=True)
class Pending[R]: reason: R # No side effect occurred, ok to retry.

@dataclass(frozen=True)
class Exhausted:
    """ ran out of iterations """

type Attempt[R, E, T] = Pending[R] | Ok[T] | Err[E]
type Result[E, T]     = Ok[T] | Err[E] | Exhausted

@dataclass(frozen=True)
class Attempts[R]:
    k: int
    elapsed: float
    reasons: tuple[R, ...]

class Wait:
    @staticmethod
    def exp(base: float = 2.0, *, cap: float = 60.0) -> Callable[[int], float]:
        return lambda n: min(base ** n, cap)
    @staticmethod
    def const(seconds: float) -> Callable[[int], float]:
        return lambda _: seconds
    @staticmethod
    def linear(step: float) -> Callable[[int], float]:
        return lambda n: step * n
    @staticmethod
    def jitter(strategy: Callable[[int], float], *, rng: Random = Random()) -> Callable[[int], float]:
        """Full jitter: uniform(0, strategy(n)). Pass a seeded Random for determinism."""
        return lambda n: rng.uniform(0, strategy(n))
