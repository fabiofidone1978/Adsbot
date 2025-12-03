**Curl examples to test rate limiting (FastAPI demo)**

Windows (cmd.exe) examples:

- Test as user (will be rate-limited after 5 requests):

```cmd
for /L %i in (1,1,6) do curl -i -H "X-API-Key: sk-user-example-1" http://127.0.0.1:8000/test
```

- Test as admin (exempt):

```cmd
for /L %i in (1,1,10) do curl -i -H "X-API-Key: sk-admin-example-1" http://127.0.0.1:8000/test
```

POSIX / PowerShell examples:

- User (POSIX):

```bash
for i in {1..6}; do curl -i -H "X-API-Key: sk-user-example-1" http://127.0.0.1:8000/test; echo; done
```

Notes:
- After the limit is exceeded you will get HTTP 429 with a `Retry-After` header in BLOCK mode.
- In SLOWDOWN mode requests beyond the limit are allowed but delayed. The middleware will add `X-RateLimit-Slowdown` and `X-RateLimit-Remaining` headers.
