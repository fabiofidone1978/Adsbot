import asyncio
import time

import pytest

from adsbot.rate_limiter import RedisRateLimiter


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.expiries = {}

    async def get(self, key):
        self._cleanup()
        v = self.store.get(key)
        return v

    async def set(self, key, value, ex: int = None):
        self.store[key] = value
        if ex:
            self.expiries[key] = time.time() + ex

    async def incr(self, key):
        self._cleanup()
        cur = int(self.store.get(key, 0))
        cur += 1
        self.store[key] = str(cur)
        return cur

    async def expire(self, key, seconds):
        self.expiries[key] = time.time() + seconds

    async def delete(self, key):
        self.store.pop(key, None)
        self.expiries.pop(key, None)

    def _cleanup(self):
        now = time.time()
        expired = [k for k, t in self.expiries.items() if t <= now]
        for k in expired:
            self.store.pop(k, None)
            self.expiries.pop(k, None)


@pytest.mark.asyncio
async def test_rate_limiter_blocks_after_limit():
    fake = FakeRedis()
    limiter = RedisRateLimiter(redis_client=fake, window_seconds=2, max_requests=3)
    api_key = "sk-user-test"

    # allow first 3
    for i in range(3):
        allowed, remaining, retry, slowdown = await limiter.increment_and_check(api_key)
        assert allowed
        assert retry is None
        assert slowdown is None

    # 4th should be blocked
    allowed, remaining, retry, slowdown = await limiter.increment_and_check(api_key)
    assert not allowed
    assert retry == 2 or retry == pytest.approx(2, rel=0.5)
    assert slowdown is None

    # wait for window expiration then allow again
    await asyncio.sleep(2.1)
    allowed, remaining, retry, slowdown = await limiter.increment_and_check(api_key)
    assert allowed
    assert slowdown is None
