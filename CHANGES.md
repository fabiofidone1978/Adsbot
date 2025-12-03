## Rate Limiter & API Keys Implementation

### Summary

This PR implements a complete rate-limiting and API key management system for Adsbot with support for both blocking and progressive slowdown strategies.

### Key Changes

#### 1. API Key Management (`adsbot/api_keys.py`)
- **Secure storage**: API keys loaded from environment variables (`ADMIN_API_KEYS`, `USER_API_KEYS`)
- **Role mapping**: `get_role(api_key)` returns 'admin', 'user', or None
- **Dynamic reload**: `reload_keys()` function allows runtime key updates without restart
- **dotenv integration**: Automatic loading from `.env` (local development) if python-dotenv is available

**Files**: `.env.example`, `.env` (local, not committed), `scripts/create_env.py` (helper to create `.env` interactively)

#### 2. Rate Limiting - Multiple Implementations

##### Redis-based (Recommended for production)
- **File**: `adsbot/rate_limiter.py`
- **Policy**: Fixed-window counter (configurable window and max requests)
- **Modes**:
  - `mode='block'` (default): Block requests with HTTP 429 + `Retry-After` header after limit exceeded
  - `mode='slowdown'`: Allow requests but apply exponential backoff delay (base 1.5, capped at 10s)
- **Admin exemption**: Keys with 'admin' role bypass all rate limits
- **Async-first**: Uses `redis.asyncio` for non-blocking operation

##### SQLite Fallback
- **File**: `adsbot/sqlite_rate_limiter.py`
- **Use case**: Environments without Redis; same async interface as RedisRateLimiter
- **In-memory support**: Configurable to use `:memory:` for testing

#### 3. Middleware & Decorators

##### FastAPI ASGI Middleware
- **File**: `adsbot/middleware_fastapi.py`
- **Features**:
  - Extracts API key from `X-API-Key` header or `?api_key=` query string
  - Routes to rate limiter based on key role
  - Returns 429 in block mode or applies delays in slowdown mode
  - Injects response headers: `X-Rate-Limit-Remaining`, `X-Rate-Limit-Slowdown` (if applicable)

##### Flask Decorator
- **File**: `adsbot/flask_decorator.py`
- **Usage**: Simple decorator for sync Flask endpoints
- **Compatibility**: Works with both Redis and SQLite limiters via `asyncio.run`

#### 4. Slowdown Algorithm

Progressive exponential backoff for requests beyond the rate limit:

```
delay = min(10.0, 0.5 * (1.5 ^ (over - 1)))
where over = current_count - max_requests
```

Example delays for `max_requests=5`:
- 6th request: ~0.75s
- 7th request: ~1.125s
- 8th request: ~1.69s
- 10th request: ~3.8s
- 12th request: 10s (capped)

#### 5. Configuration

**Environment Variables**:
```env
ADMIN_API_KEYS=sk-admin-key-1,sk-admin-key-2
USER_API_KEYS=sk-user-key-1,sk-user-key-2
REDIS_URL=redis://localhost:6379/0  # optional; defaults to localhost:6379/0
```

**Rate Limiter Initialization**:
```python
from adsbot.rate_limiter import RedisRateLimiter

# Block mode (default)
limiter = RedisRateLimiter(window_seconds=60, max_requests=5, mode="block")

# Slowdown mode
limiter = RedisRateLimiter(window_seconds=60, max_requests=5, mode="slowdown")
```

**FastAPI Integration**:
```python
from fastapi import FastAPI
from adsbot.rate_limiter import RedisRateLimiter
from adsbot.middleware_fastapi import RateLimitMiddleware

app = FastAPI()
limiter = RedisRateLimiter()
app.add_middleware(RateLimitMiddleware, limiter=limiter)
```

#### 6. Testing

**Files**:
- `tests/test_rate_limiter.py` — Redis limiter with FakeRedis in-memory backend
- `tests/test_sqlite_rate_limiter.py` — SQLite limiter tests
- `tests/test_rate_limiter_slowdown.py` — Slowdown mode validation

**Run tests**:
```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

**Example outputs** (after running 6 requests as user with `max_requests=5`):
- Block mode: HTTP 429 on 6th request
- Slowdown mode: HTTP 200 on 6th request, but with ~0.75s delay

#### 7. CI/CD

**File**: `.github/workflows/python-tests.yml`
- Runs on push and pull requests to main/master
- Installs both `requirements.txt` and `requirements-dev.txt`
- Executes `pytest -q`

#### 8. Documentation

- `docs/RATE_LIMITING.md` — Configuration and integration guide
- `docs/CURL_EXAMPLES.md` — curl command examples for testing behavior
- `examples/app_rate_limit.py` — Minimal FastAPI demo app

#### 9. Security Considerations

- **No secrets in repo**: `.env` and `.env.local` are in `.gitignore`
- **Example file**: `.env.example` contains placeholders only
- **Key rotation**: Use `reload_keys()` after updating env vars (e.g., if keys compromised)
- **Secret manager**: For production, use Azure Key Vault, AWS Secrets Manager, or similar

### Breaking Changes

None. New feature set; existing code unaffected.

### Migration Path

If integrating into an existing Telegram bot:

1. Add `.env` with real API keys and credentials (not committed)
2. Initialize rate limiter:
   ```python
   from adsbot.rate_limiter import RedisRateLimiter
   limiter = RedisRateLimiter()
   ```
3. Add middleware (for web API endpoints) or wrap handlers with decorator
4. Run tests: `pytest -q`

### Dependencies Added

**Runtime**: `redis>=4.6.0,<6.0` (optional; required for Redis limiter)

**Dev/Test**: `pytest==7.4.0`, `pytest-asyncio==0.21.0`

### Files Changed

**New files**:
- `adsbot/rate_limiter.py`
- `adsbot/sqlite_rate_limiter.py`
- `adsbot/middleware_fastapi.py`
- `adsbot/flask_decorator.py`
- `adsbot/api_keys.py` (modified earlier; dotenv support added)
- `.env.example`
- `.gitignore` (updated to exclude `.env`)
- `scripts/create_env.py`
- `examples/app_rate_limit.py`
- `requirements-dev.txt`
- `.github/workflows/python-tests.yml`
- `docs/RATE_LIMITING.md`
- `docs/CURL_EXAMPLES.md`
- `tests/test_rate_limiter.py`
- `tests/test_sqlite_rate_limiter.py`
- `tests/test_rate_limiter_slowdown.py`

**Modified files**:
- `requirements.txt` (added redis, moved pytest to requirements-dev.txt)

### Testing the Feature

```bash
# Start a Redis server (or use in-memory SQLite limiter)
# redis-server

# Run the demo FastAPI app
uvicorn examples.app_rate_limit:app --reload --port 8000

# In another terminal, send requests as a user (rate-limited)
for i in {1..6}; do
  curl -i -H "X-API-Key: sk-user-example-1" http://127.0.0.1:8000/test
  echo
done

# Send requests as admin (exempt)
for i in {1..10}; do
  curl -i -H "X-API-Key: sk-admin-example-1" http://127.0.0.1:8000/test
done
```

See `docs/CURL_EXAMPLES.md` for detailed examples.

### Notes

- Slowdown backoff coefficient and cap (10s) are tunable in `adsbot/rate_limiter.py`
- SQLite limiter keeps in-memory DB for tests; provide a file path for persistence
- Redis connection is lazy-initialized on first request (not at app startup)
- Admin keys are always exempt; only 'user' keys are rate-limited

### Author

Adsbot Team

### Date

December 3, 2025
