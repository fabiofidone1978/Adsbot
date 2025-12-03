"""Redis-backed rate limiter for Adsbot

Provides a small RedisRateLimiter class and a helper decorator for sync/async
handlers. Uses fixed-window counters and sets a "blocked_until" key when the
limit is exceeded.

This module accepts a redis client instance (redis.asyncio.Redis) for testability.
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

try:
    import redis.asyncio as aioredis
except Exception:  # pragma: no cover - import issues on systems without redis
    aioredis = None  # type: ignore

from adsbot import api_keys


class RedisRateLimiter:
    def __init__(self, *, redis_client=None, window_seconds: int = 60, max_requests: int = 5, mode: str = "block"):
        """Create a rate limiter.

        Args:
            redis_client: an instance compatible with redis.asyncio.Redis (optional)
            window_seconds: size of fixed window in seconds
            max_requests: allowed requests per window before blocking
        """
        self.window = int(window_seconds)
        self.max_requests = int(max_requests)
        self._redis = redis_client
        # mode: 'block' or 'slowdown'
        if mode not in ("block", "slowdown"):
            raise ValueError("mode must be 'block' or 'slowdown'")
        self.mode = mode

    async def _get_redis(self):
        if self._redis is not None:
            return self._redis
        if aioredis is None:
            raise RuntimeError("redis.asyncio is not available; install redis package")
        self._redis = aioredis.Redis.from_url("redis://localhost:6379/0")
        return self._redis

    def _window_start(self, now: Optional[float] = None) -> int:
        if now is None:
            now = time.time()
        return int(now // self.window) * self.window

    async def increment_and_check(self, api_key: str) -> Tuple[bool, int, Optional[int], Optional[float]]:
        """Increment counter for api_key and check status.

        Returns (allowed, remaining, retry_after_seconds_or_None, slowdown_seconds_or_None)
        - If `mode=='block'` and limit exceeded: returns (False, 0, retry_after, None)
        - If `mode=='slowdown'` and limit exceeded: returns (True, 0, None, slowdown_seconds)
        """
        redis = await self._get_redis()
        now = int(time.time())
        window_start = self._window_start(now)
        count_key = f"rl:{api_key}:count:{window_start}"
        blocked_key = f"rl:{api_key}:blocked"

        # Check blocked first
        blocked_until = await redis.get(blocked_key)
        if blocked_until:
            try:
                blocked_ts = int(blocked_until)
            except Exception:
                blocked_ts = 0
            if blocked_ts > now:
                return False, 0, blocked_ts - now, None
            else:
                # expired block; delete
                await redis.delete(blocked_key)

        # Increment the counter for current window
        cur = await redis.incr(count_key)
        # Set TTL so window expires
        await redis.expire(count_key, self.window + 5)

        remaining = max(0, self.max_requests - int(cur))
        if int(cur) > self.max_requests:
            if self.mode == "block":
                # Block for one full window
                blocked_until_ts = now + self.window
                await redis.set(blocked_key, str(blocked_until_ts), ex=self.window + 5)
                return False, 0, self.window, None
            else:
                # Slowdown mode: exponential backoff (base 1.5)
                over = int(cur) - self.max_requests
                # Formula: 0.5 * (1.5 ^ (over - 1)), capped at 10s
                delay = min(10.0, 0.5 * (1.5 ** (over - 1)))
                return True, 0, None, float(delay)

        return True, remaining, None, None

    async def is_blocked(self, api_key: str) -> Optional[int]:
        """Return seconds until unblocked or None."""
        redis = await self._get_redis()
        now = int(time.time())
        blocked_key = f"rl:{api_key}:blocked"
        blocked_until = await redis.get(blocked_key)
        if not blocked_until:
            return None
        try:
            blocked_ts = int(blocked_until)
        except Exception:
            return None
        if blocked_ts > now:
            return blocked_ts - now
        # expired
        await redis.delete(blocked_key)
        return None


__all__ = ["RedisRateLimiter"]
