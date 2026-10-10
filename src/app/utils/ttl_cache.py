"""Small time-based cache for expensive upstream lookups."""
from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from time import monotonic
from typing import Any


def ttl_cache(seconds: float) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Cache a function's result per positional-argument tuple for ``seconds``.

    State lives in the process (one Worker isolate), so a long-lived process
    refetches at most once per window. The wrapped function gains ``cache_clear()``.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        entries: dict[tuple[Any, ...], tuple[float, Any]] = {}

        @wraps(func)
        def wrapper(*args: Any) -> Any:
            cached = entries.get(args)
            if cached is not None and monotonic() - cached[0] < seconds:
                return cached[1]
            value = func(*args)
            entries[args] = (monotonic(), value)
            return value

        wrapper.cache_clear = entries.clear  # type: ignore[attr-defined]
        return wrapper

    return decorator
