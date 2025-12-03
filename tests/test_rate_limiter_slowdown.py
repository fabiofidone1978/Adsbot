import pytest

from adsbot.rate_limiter import RedisRateLimiter


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.expiries = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex: int = None):
        self.store[key] = value

    async def incr(self, key):
        cur = int(self.store.get(key, 0))
        cur += 1
        self.store[key] = str(cur)
        return cur

    async def expire(self, key, seconds):
        pass

    async def delete(self, key):
        self.store.pop(key, None)


@pytest.mark.asyncio
async def test_slowdown_returns_delay():
    fake = FakeRedis()
    limiter = RedisRateLimiter(redis_client=fake, window_seconds=60, max_requests=3, mode="slowdown")
    key = "sk-user-test-slow"

    # first 3: no slowdown
    for i in range(3):
        allowed, remaining, retry, slowdown = await limiter.increment_and_check(key)
        assert allowed
        assert slowdown is None

    # 4th: allowed but with slowdown > 0 (exponential backoff: 0.5 * 1.5^0 = 0.5)
    allowed, remaining, retry, slowdown = await limiter.increment_and_check(key)
    assert allowed
    assert slowdown is not None
    assert slowdown >= 0.5

