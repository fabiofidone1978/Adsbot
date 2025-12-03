import asyncio

import pytest

from adsbot.sqlite_rate_limiter import SQLiteRateLimiter


@pytest.mark.asyncio
async def test_sqlite_rate_limiter_blocks_after_limit():
    limiter = SQLiteRateLimiter(db_path=":memory:", window_seconds=2, max_requests=3)
    api_key = "sk-user-test-sqlite"

    # first 3 allowed
    for i in range(3):
        allowed, remaining, retry = await limiter.increment_and_check(api_key)
        assert allowed
        assert retry is None

    # 4th blocked
    allowed, remaining, retry = await limiter.increment_and_check(api_key)
    assert not allowed
    assert retry == 2 or pytest.approx(retry, rel=0.5)

    # wait and allow again
    await asyncio.sleep(2.1)
    allowed, remaining, retry = await limiter.increment_and_check(api_key)
    assert allowed
