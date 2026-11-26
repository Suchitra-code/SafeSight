"""
Thread-safe In-Memory Analytics Cache for SafeSight AI.
Caches heavy SQL aggregation and analytics results for 10-15 seconds,
dramatically improving website loading performance on Render Free Tier.
Auto-invalidates immediately when new violations are recorded or statuses change.
"""
import time
import threading
from functools import wraps
import logging

logger = logging.getLogger(__name__)

_cache = {}
_lock = threading.Lock()
_MAX_ENTRIES = 500
_DEFAULT_TTL = 15.0  # seconds


def _make_hashable(obj):
    """Recursively converts dicts, lists, and sets into hashable tuples."""
    try:
        if isinstance(obj, dict):
            return tuple(sorted((k, _make_hashable(v)) for k, v in obj.items()))
        elif isinstance(obj, (list, tuple, set)):
            return tuple(_make_hashable(x) for x in obj)
        return obj
    except Exception:
        return repr(obj)


def cached_analytics(ttl: float = _DEFAULT_TTL):
    """
    Decorator for caching analytics function calls.
    Keys are derived from function name and serialized arguments.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                key_args = tuple(_make_hashable(a) for a in args)
                key_kwargs = tuple((k, _make_hashable(v)) for k, v in sorted(kwargs.items()))
                cache_key = (fn.__module__, fn.__name__, key_args, key_kwargs)
            except Exception:
                # Fallback to direct execution if unhashable
                return fn(*args, **kwargs)

            now = time.time()

            with _lock:
                entry = _cache.get(cache_key)
                if entry is not None:
                    value, expires_at = entry
                    if now < expires_at:
                        return value
                    else:
                        _cache.pop(cache_key, None)

            # Compute outside the lock to avoid blocking other threads
            result = fn(*args, **kwargs)

            with _lock:
                if len(_cache) >= _MAX_ENTRIES:
                    # Prune expired entries
                    expired_keys = [k for k, (_, exp) in _cache.items() if now >= exp]
                    for k in expired_keys:
                        _cache.pop(k, None)
                    # If still at capacity, clear oldest quarter
                    if len(_cache) >= _MAX_ENTRIES:
                        _cache.clear()
                _cache[cache_key] = (result, now + ttl)

            return result
        return wrapper
    return decorator


def clear_analytics_cache():
    """Invalidates the entire analytics cache on database mutations."""
    with _lock:
        count = len(_cache)
        _cache.clear()
        if count > 0:
            logger.debug(f"Cleared analytics cache ({count} entries).")
