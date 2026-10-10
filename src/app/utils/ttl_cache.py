"""Small time-based cache for expensive upstream lookups."""
from __future__ import annotations

from collections.abc import Callable
from functools import update_wrapper
from time import monotonic
from typing import Any


class TTLCached[**P, R]:
    """A function whose result is kept per argument tuple for ``seconds``; ``cache_clear()`` empties it."""

    def __init__(self, func: Callable[P, R], seconds: float) -> None:
        self._func = func
        self._seconds = seconds
        self._entries: dict[tuple[Any, ...], tuple[float, R]] = {}
        update_wrapper(self, func)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        key = (*args, *sorted(kwargs.items()))
        cached = self._entries.get(key)
        if cached is not None and monotonic() - cached[0] < self._seconds:
            return cached[1]
        value = self._func(*args, **kwargs)
        self._entries[key] = (monotonic(), value)
        return value

    def cache_clear(self) -> None:
        self._entries.clear()


def ttl_cache(seconds: float):
    """Cache a function's result per argument tuple for ``seconds``.

    State lives in the process (one Worker isolate), so a long-lived process
    refetches at most once per window. The wrapped function gains ``cache_clear()``.
    """

    def decorator[**P, R](func: Callable[P, R]) -> TTLCached[P, R]:
        return TTLCached(func, seconds)

    return decorator
