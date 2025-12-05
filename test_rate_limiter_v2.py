"""Quick test of the new atomic SQLite rate limiter."""
import sys
sys.path.insert(0, r'd:\Documents and Settings\fabio-fidone\My Documents\Adsbot')

from adsbot.sqlite_rate_limiter_v2 import SQLiteRateLimiter
import asyncio
import time
import threading

async def test_basic():
    """Test basic rate limiting."""
    limiter = SQLiteRateLimiter(":memory:", window_seconds=10, max_requests=5)
    
    print("Testing basic rate limiting...")
    for i in range(8):
        allowed, remaining, retry_after = await limiter.increment_and_check("test_key")
        print(f"  Request {i+1}: allowed={allowed}, remaining={remaining}, retry_after={retry_after}")
    
    print("✓ Basic test passed")

async def test_concurrent():
    """Test concurrent access."""
    limiter = SQLiteRateLimiter(":memory:", window_seconds=60, max_requests=50)
    
    async def worker(worker_id, count):
        results = []
        for i in range(count):
            allowed, remaining, retry_after = await limiter.increment_and_check(f"key_{worker_id % 3}")
            results.append((allowed, remaining, retry_after))
        return results
    
    print("Testing concurrent access (10 workers x 10 requests)...")
    tasks = [worker(i, 10) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    total_allowed = sum(1 for r in results for allowed, _, _ in r if allowed)
    print(f"  Total allowed: {total_allowed} / 100")
    print(f"  Expected: ~50 (50 requests max per window)")
    
    print("✓ Concurrent test passed")

async def test_stress():
    """Stress test with rapid concurrent requests."""
    limiter = SQLiteRateLimiter(":memory:", window_seconds=60, max_requests=100)
    
    async def stress_worker(worker_id):
        results = []
        for i in range(50):
            allowed, remaining, retry_after = await limiter.increment_and_check("stress_key")
            results.append(allowed)
        return results
    
    print("Testing stress (20 workers x 50 requests each)...")
    start = time.time()
    tasks = [stress_worker(i) for i in range(20)]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start
    
    total_allowed = sum(1 for r in results for allowed in r if allowed)
    total_blocked = sum(1 for r in results for allowed in r if not allowed)
    print(f"  Elapsed: {elapsed:.2f}s")
    print(f"  Total allowed: {total_allowed}")
    print(f"  Total blocked: {total_blocked}")
    print(f"  Expected: ~100 allowed, ~900 blocked")
    
    if total_allowed > 0 and total_blocked > 0:
        print("✓ Stress test passed")
    else:
        print("✗ Stress test failed - wrong distribution")

async def main():
    try:
        await test_basic()
        await test_concurrent()
        await test_stress()
        print("\n✓ All tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
