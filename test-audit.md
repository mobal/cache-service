# Test Coverage & Edge-Case Audit

Generated: 2026-06-11

---

## 1. Untested Production Code

### `api_handler.py` — 80% coverage, 10 missing lines

| Lines | What | Why untested |
|-------|------|-------------|
| `22→25` | `set_package_logger()` branch | Only the `if settings.debug:` taken-branch is exercised; no test runs with `DEBUG=false` to hit the skip-branch |
| `70–97` | `botocore_error_handler` body | No test triggers an unhandled `Exception` or `BotoCoreError` |
| `142–143` | `@app.exception_handler(...)` def lines | The function is registered but never called in tests (see above) |
| `147` | `if __name__ == "__main__"` | The module is imported, never run as a script |

**Impact**: The entire error-response contract for 500s is unverified. If DynamoDB is unreachable, the API returns a `JSONResponse` with `ErrorResponse` shape — but no test asserts that shape.

---

## 2. Missing Edge Cases in Tests

### A: Service layer — `CacheService`

| Edge case | Where it matters | Status |
|-----------|------------------|--------|
| **Repository raises exception** on `get_key_value_by_key` or `create_key_value` | `services.py:37`, `services.py:51` — exception propagates unmodified | ❌ Untested |
| **Repository returns dict with missing fields** (e.g. no `created_at`) | `services.py:41` — `KeyValue(**item)` pydantic validation raises | ❌ Untested |
| **Repository returns dict with extra fields** | `services.py:41` — pydantic silently drops extras with default config | ❌ Untested (silent behaviour, may mask bugs) |
| **`create_key_value` mutates the input dict** | `services.py:49-50` — adds `created_at`, converts `ttl` in-place | ⚠️ Tested implicitly (the assert checks the mutated dict), but the side effect is never explicitly documented or guarded |
| **`key` is empty string** | Passes schema validation, then hits DynamoDB | ❌ Untested |
| **`ttl` is `0` (falsy)** | `create_dict.get("ttl")` → `0` → falsy → treated as "no ttl" | ❌ Untested |

### B: Repository layer — `CacheRepository`

| Edge case | Where it matters | Status |
|-----------|------------------|--------|
| **Overwrite existing key** | `repositories.py:18` — `put_item` silently replaces | ❌ Untested (may be intentional upsert) |
| **DynamoDB error** (throttling, network failure) | `repositories.py:18,21` — exception propagates | ❌ Untested |
| **Unicode/special characters in key** | `repositories.py:21` — `get_item(Key={"key": key})` | ❌ Untested |
| **Empty value** (`""`, `None`, `{}`) | `repositories.py:18` — `put_item(Item=data)` | ❌ Untested |

### C: API integration — `TestCacheApi`

| Edge case | Where it matters | Status |
|-----------|------------------|--------|
| **`GET /health`** | `api_handler.py:140-143` | ❌ Never called in any test |
| **POST without `ttl`** | Schema marks `ttl` optional | ❌ Only tested at unit level, never at integration |
| **POST with invalid `ttl`** (`0`, `-1`, `"abc"`) | `schemas.py:11` — `conint(gt=0)` | ❌ Untested |
| **POST missing `key`** | Should fail 400 | ❌ Untested (only empty body is tested) |
| **POST missing `value`** | Should fail 400 | ❌ Untested |
| **Error response schema for 400** | `api_handler.py:129-135` — `ValidationErrorResponse` shape | ❌ Untested (status code asserted, body not) |
| **Error response schema for 500** | `api_handler.py:93-99` — `ErrorResponse` shape | ❌ Untested |
| **`expiredAt` field in response** | `services.py:24-28` — computed field on `KeyValue` | ❌ Never asserted in integration tests |
| **`X-Correlation-ID` header in response** | `middlewares.py:49` | ❌ Never asserted |
| **CORS headers** | `api_handler.py:28-33` | ❌ Never asserted |

---

## 3. Code Quality / Design Observations

### `create_key_value` mutates the caller's dict
`services.py:49-50`:
```python
create_dict["created_at"] = pendulum.now("UTC").to_iso8601_string()
create_dict["ttl"] = expired_at.int_timestamp if expired_at else None
```

This modifies the dict the caller passed in. A caller who reuses the dict after calling `create_key_value` will find it enriched/altered. The service tests mask this because `data` is a local variable discarded after each test.

**Recommended fix**: Create a copy internally (`data = {**create_dict}`) or build a new dict to pass downstream.

### `botocore_error_handler` catches `Exception` broadly
`api_handler.py:68` — the `@app.exception_handler(Exception)` decorator catches literally everything, including `KeyValueNotFoundException` (via `HTTPException`). FastAPI's handler resolution uses MRO, so `HTTPException` is correctly routed to `http_exception_handler` and `KeyValueNotFoundException` inherits that. But this is fragile: if the decorator order or MRO ever changes, errors could be swallowed by the wrong handler with a misleading 500 `ErrorResponse`.

### SSM `api_key` has no fallback if env var is unset
`settings.py:21`:
```python
parameters.get_parameter(
    os.environ.get("CACHE_SERVICE_API_KEY_SSM_PARAM_NAME"), decrypt=True
)
```

If `CACHE_SERVICE_API_KEY_SSM_PARAM_NAME` is not set, `get_parameter(None, ...)` is called. The SSM client would likely throw — and since this runs in `api_key` via `@cached_property`, it fails on first access at middleware registration time (`api_handler.py:34`). Not a test gap per se, but a brittle production path with no coverage.

---

## 4. Summary of Highest-Impact Gaps

1. **500 error contract is completely untested** — the `botocore_error_handler` and its `ErrorResponse` shape. If DynamoDB goes down, the customer gets an unverified response format.
2. **No error-injection tests** — the service and repository layers have zero tests for what happens when a dependency fails (network timeout, throttling, auth error).
3. **`expiredAt` field never verified** — this computed field is part of the API contract but invisible to tests.
4. **Correlation ID header never verified** — middleware sets it, nobody checks it.
5. **`create_key_value` mutation side-effect** — not a test gap but a latent bug that tests happen not to trigger.
