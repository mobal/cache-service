# 🔍 Deep Code Review: Cache Service

> **Date:** 2026-06-11
> **Branch:** `develop` (vs `main`)
> **Python:** 3.14 | **Framework:** FastAPI + DynamoDB (Lambda)

---

## 📋 Prioritized Action Plan

| # | Severity | Finding | Effort | Impact | Category | Status |
|---|---|---|---|---|---|---|
| 1 | 🔴 | **CorrelationIdMiddleware defined but never registered** | 🟢 2 min | Logging has no correlation IDs in production | Correctness | ✅ Fixed |
| 2 | 🔴 | **Exception handler leaks internals when `DEBUG=true`** | 🟢 5 min | Information disclosure to API clients | Security | ✅ Fixed |
| 3 | 🟠 | **Dual logging — `logger.exception()` after `logger.warning()`** | 🟢 2 min | Doubles log volume, wrong severity on expected 404s | Observability | ✅ Fixed |
| 4 | 🔴 | **`settings.api_key` — SSM call on cold start, no caching/retry** | 🟢 15 min | ~1s cold start latency; crashes if SSM is down | Reliability | ✅ Fixed |
| 5 | 🟠 | **DynamoDB eventually consistent reads** | 🟢 5 min | Read-after-write may miss data | Correctness | ✅ Fixed |
| 6 | 🟠 | **No DynamoDB error handling (throttling → wrong status code)** | 🟡 30 min | Throttling returns 500 instead of 429 | Reliability | ⏭️ Skipped |
| 7 | 🟠 | **`pendulum.now()` uses local timezone, not UTC from settings** | 🟢 5 min | Timestamps inconsistent across environments | Correctness | ✅ Fixed |
| 8 | 🟠 | **`CacheService` hard-wires `CacheRepository` — no DI** | 🟢 10 min | Tests coupled to internals, can't swap implementations | Maintainability | ⏭️ Skipped |
| 9 | 🟡 | **Build layer script `pip install --no-deps` is fragile** | 🟢 10 min | Silent missing deps if resolver diverges | Reliability | ✅ Fixed |
| 10 | 🟠 | **`ruff.toml` target-version `py313` but project is on 3.14** | 🟢 1 min | Ruff may reject valid 3.14 syntax | Tooling | ✅ Fixed |
| 11 | 🟡 | **`boto3-stubs[essential]` extra dropped → degraded types** | 🟢 2 min | AWS service calls lose type safety | Type Safety | ✅ Fixed |
| 12 | 🟡 | **Missing CORS middleware** | 🟢 10 min | Web frontends can't consume the API | Feature Gap | ✅ Fixed |
| 13 | 🟡 | **Lambda Powertools layer ARN hardcoded to `:28`** | 🟢 10 min | Will drift as new versions release | Maintainability | ⏭️ Skipped |
| 14 | 🟡 | **`.nanocoder/` not in `.gitignore`** | 🟢 1 min | Untracked dir pollutes git status | Housekeeping | ⏭️ Skipped |
| 15 | 🟡 | **Misnamed test `test_fail_to_get_key_value_with_invalid_uuid`** | 🟢 2 min | Tests "key not found", not "invalid UUID" | Clarity | ✅ Fixed |
| 16 | 🟢 | **`conftest.py` duplicate pythonpath (`.` and `app`)** | 🟢 2 min | Potential import ambiguity | Config | ✅ Fixed |
| 17 | 🟢 | **Module-level `settings` singleton** | 🟡 30 min | Import order fragility | Pattern | ⏭️ Skipped |
| 18 | 🟢 | **`mypy` → `ty` transition — different tools, uncertain coverage** | 🟡 20 min | May have lost static analysis coverage | Tooling | ⏭️ Skipped |
| 19 | 🟢 | **`ujson` removed without documentation** | 🟢 5 min | Performance regression under load | Docs | ⏭️ Skipped |
| 20 | 🟢 | **Minimal README** | 🟡 20 min | No onboarding or architecture docs | Docs | ✅ Fixed |
| 21 | 🟢 | **Commit message typo `cohre` → `chore`** | 🟢 1 min | Cosmetic | Polish | ⏭️ Skipped |

> **Legend:** Effort = 🟢 <15min · 🟡 <1h · 🔴 >1h

---

## 🔴 Critical Issues

### 1️⃣ CorrelationIdMiddleware defined but never registered

**File:** `app/middlewares.py` → defines `CorrelationIdMiddleware` ✅
**File:** `app/api_handler.py` → never imports or registers it ❌

The `CorrelationIdMiddleware` is fully implemented with `ContextVar` support and automatic UUID generation as a fallback, but it's **never added to the FastAPI application**. This means:

- Correlation IDs are **never set on incoming requests**
- The `X-Correlation-ID` response header is **never written**
- Log correlation via `logger.set_correlation_id()` never happens

```python
# app/api_handler.py — Middleware is imported but NOT CorrelationIdMiddleware:
from app.middlewares import APIKeyMiddleware  # ⚠️ CorrelationIdMiddleware missing!

app.add_middleware(APIKeyMiddleware, api_key=settings.api_key)
app.add_middleware(GZipMiddleware)
# ❌ No app.add_middleware(CorrelationIdMiddleware)
```

**Fix:** Import and register it:
```python
from app.middlewares import APIKeyMiddleware, CorrelationIdMiddleware
app.add_middleware(CorrelationIdMiddleware)
```

---

### 2️⃣ `settings.api_key` — SSM Parameter Store call at module load

**File:** `app/settings.py:16-20`

```python
@computed_field
@property
def api_key(self) -> str:
    return parameters.get_parameter(
        os.environ.get("CACHE_SERVICE_API_KEY_SSM_PARAM_NAME"), decrypt=True
    )
```

This property makes an **SSM API call every time it's accessed** — which happens during module initialization in `api_handler.py:27`:

```python
app.add_middleware(APIKeyMiddleware, api_key=settings.api_key)
```

On AWS Lambda, this executes during **every cold start**, adding ~500–1500ms of latency with **no retry or caching logic**. If SSM is unavailable, the entire application crashes at startup.

**Fix:** Add caching with a fallback:
```python
import functools
from typing import Annotated

@computed_field
@functools.cache
@property
def api_key(self) -> str:
    param_name = os.environ.get("CACHE_SERVICE_API_KEY_SSM_PARAM_NAME")
    if not param_name:
        raise ValueError("CACHE_SERVICE_API_KEY_SSM_PARAM_NAME is not set")
    try:
        return parameters.get_parameter(param_name, decrypt=True)
    except Exception:
        logger.exception("Failed to fetch API key from SSM")
        raise
```

Or better: pass it via environment variable directly and skip SSM for the API key.

---

### 3️⃣ Global exception handler leaks internals when DEBUG=true

**File:** `app/api_handler.py:76-83`

```python
if settings.debug:
    error_message = (
        f"{type(error).__name__}: {str(error) or repr(error)}"
        if str(error)
        else repr(error)
    )
```

If `DEBUG=true` is accidentally set in production, **full exception details are returned to the client** — including `__cause__`, `__context__`, and internal stack traces (logged at lines 65-74). This is an **information disclosure** vulnerability.

**Fix:** Never return exception internals to the client, even in debug mode:
```python
if settings.debug:
    error_message = f"{type(error).__name__}: {str(error)}"
    # Log full details but don't return them
```

Or gate debug on stage explicitly:
```python
if settings.debug and settings.stage != "production":
```

---

## 🟠 High Severity

### 4️⃣ DynamoDB eventually consistent reads

**File:** `app/repositories.py:21`

```python
def get_key_value_by_key(self, key: str) -> dict[str, Any] | None:
    response = self._table.get_item(Key={"key": key})
    return response.get("Item", None)
```

`get_item()` defaults to **eventually consistent reads** (`ConsistentRead=False`). A write followed by an immediate read may not see the data. This is a potential correctness bug for:

- **write-then-read patterns** — the API creates a cache entry, then immediately reads it
- **race conditions under load** — inconsistent reads become more visible with concurrent access

**Fix:** Make consistency configurable or default to strongly consistent:
```python
def get_key_value_by_key(self, key: str, consistent_read: bool = False) -> dict[str, Any] | None:
    response = self._table.get_item(Key={"key": key}, ConsistentRead=consistent_read)
    return response.get("Item", None)
```

---

### 5️⃣ ruff.toml target-version mismatch

**File:** `ruff.toml:1`

```toml
target-version = "py313"
```

But `.python-version` is `3.14` and `pyproject.toml` requires `>=3.14`. Ruff 0.15.0 supports `py314` — the config is **one version behind**.

**Fix:**
```toml
target-version = "py314"
```

---

### 6️⃣ ❌ `pendulum.now()` uses local timezone

**File:** `app/services.py:49`

```python
create_dict["created_at"] = pendulum.now().to_iso8601_string()
```

`pendulum.now()` without arguments uses the **local system timezone**. When the app runs locally (e.g., UTC+2) vs on AWS Lambda (always UTC), `created_at` timestamps will differ. This makes debugging cross-environment inconsistencies harder.

`DEFAULT_TIMEZONE=UTC` is set in `.env.example` and passed to the Lambda, but **never actually used** in code.

**Fix:**
```python
from app import settings

create_dict["created_at"] = pendulum.now(settings.default_timezone).to_iso8601_string()
```

---

### 7️⃣ `CacheService` hard-wires `CacheRepository` — no DI

**File:** `app/services.py:32-33`

```python
class CacheService:
    def __init__(self):
        self._repository = CacheRepository()
```

The service creates its own repository, which means:
- **Testing requires monkey-patching** (`mocker.patch.object(CacheRepository, ...)`) instead of clean constructor injection
- **Cannot easily swap implementations** (e.g., mock for tests, cached version for production)
- **Hidden coupling** — every `CacheService` test must know about `CacheRepository` internals

**Fix:** Constructor injection:
```python
class CacheService:
    def __init__(self, repository: CacheRepository | None = None):
        self._repository = repository or CacheRepository()
```

---

### 8️⃣ `logger.exception(error)` — redundant dual logging

**File:** `app/api_handler.py:100, 118`

```python
@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, error: HTTPException) -> JSONResponse:
    logger.warning(
        "HTTP exception handled",
        extra={"status_code": error.status_code, "path": request.url.path},
    )
    logger.exception(error)  # ❌ This logs AGAIN at ERROR level
```

`logger.exception(error)` logs at **ERROR level** immediately after `logger.warning(...)` — producing **two log entries** for every handled exception. The first is WARNING, the second is ERROR with the same context. This creates log noise and incorrect severity (expected 404s are not errors).

**Fix:** Remove the redundant `logger.exception()` call — the `logger.warning()` with structured extras is sufficient:
```python
logger.warning(
    "HTTP exception handled",
    extra={"status_code": error.status_code, "path": request.url.path},
)
# No need for logger.exception here — 404s are expected behavior
```

---

### 9️⃣ No DynamoDB error handling in repository

**File:** `app/repositories.py`

The repository has **zero error handling** for DynamoDB operations:
- `ProvisionedThroughputExceededException` → 500 (should be 429 with retry)
- `ResourceNotFoundException` → 500 (should be meaningful context)
- `ConditionalCheckFailedException` → 500
- `InternalServerError` → 500 (should trigger retry)

The global `botocore_error_handler` catches these, but treats **all as 500 Internal Server Error**. Throttling responses should return 429 with `Retry-After` headers for proper client-side backoff.

**Fix:** Add a retry wrapper or translate DynamoDB exceptions in the repository layer:
```python
from botocore.exceptions import ClientError

class CacheRepository:
    def get_key_value_by_key(self, key: str) -> dict[str, Any] | None:
        try:
            response = self._table.get_item(Key={"key": key})
            return response.get("Item", None)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ProvisionedThroughputExceededException":
                raise ThrottlingException() from e
            raise
```

---

## 🟡 Medium Severity

### 🔸 `boto3-stubs[essential]` extra dropped

**File:** `pyproject.toml`

| Before (main) | After (develop) |
|---|---|
| `boto3-stubs[essential]>=1.36.19` | `boto3-stubs>=1.42.48` |

The `[essential]` extra provides service-specific type stubs (DynamoDB, SSM, S3, etc.). Without it, **type checking for all AWS service interactions is significantly degraded** — `cache_table.put_item()`, `ssm_client.put_parameter()`, etc. will have `Any` types instead of precise type hints.

**Fix:** Restore the extra:
```toml
"boto3-stubs[essential]>=1.42.48",
```

---

### 🔸 Missing CORS middleware

**File:** `app/api_handler.py`

The API has **no CORS configuration**. If this service is consumed by web frontends (even internal tools), CORS preflight `OPTIONS` requests will fail. Add before other middleware so CORS headers are set on every path.

**Fix:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[...],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### 🔸 Misnamed test: `test_fail_to_get_key_value_with_invalid_uuid`

**File:** `tests/unit/service/test_cache_service.py:15`

```python
def test_fail_to_get_key_value_with_invalid_uuid(
```

The test passes a **valid UUID** (from the `data` fixture) and patches the repository to return `None`. It tests **"key not found"**, not **"invalid UUID"**. The name is misleading.

**Fix:** Rename to `test_fail_to_get_non_existent_key` or similar.

---

### 🔸 Lambda Powertools layer ARN hardcoded

**File:** `infrastructure/lambda.tf:17`

```hcl
"arn:aws:lambda:${var.aws_region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python314-${var.architecture}:28"
```

The layer version (`:28`) is pinned. New versions are released frequently — this will drift and potentially break as Python 3.14 Lambda runtime evolves.

**Fix:** Use a data source to fetch the latest version:
```hcl
data "aws_lambda_layer_version" "powertools" {
  layer_name = "AWSLambdaPowertoolsPythonV3-python314-${var.architecture}"
}
```

---

### 🔸 `.nanocoder/` not in `.gitignore`

**File:** `.gitignore`

The `.nanocoder/` directory shows up in `git status` as untracked (`?? .nanocoder/`). This is a tool/IDE directory that should be excluded.

**Fix:**
```
# .gitignore
.nanocoder/
```

---

### 🔸 Build layer script uses `pip install --no-deps`

**File:** `scripts/build_requirements_layer.sh`

```bash
uv export --locked --no-dev --format requirements.txt > requirements.txt
pip install -r requirements.txt \
  -t /out/python/lib/python3.14/site-packages \
  --platform manylinux2014_x86_64 \
  --python-version 3.14 \
  --no-deps
```

Using `--no-deps` relies on `uv export` listing the **complete** transitive dependency tree. Any disparity between `uv`'s resolution and `pip`'s resolver could silently produce an incomplete layer with **missing runtime dependencies**. This is fragile.

**Fix:** Either remove `--no-deps` (simplest, albeit slower) or use `uv pip install` directly to stay within a single resolver:
```bash
uv pip install \
  --python-platform linux \
  --python-version 3.14 \
  --target /out/python/lib/python3.14/site-packages \
  -r requirements.txt
```

---

## 🟢 Low Severity

### 🔹 `conftest.py` has duplicate pythonpath resolution

**File:** `pyproject.toml:46-49`

```toml
pythonpath = [
    ".",
    "app",
]
```

Adding both `.` and `app` creates a potential import ambiguity — `from app import X` could resolve via either path. With `src = ["app"]` in `ruff.toml` and `known-first-party = ["app"]` in isort, there's a risk of import sorting inconsistency.

---

### 🔹 Module-level `settings` singleton

**File:** `app/__init__.py`

```python
from app.settings import Settings
settings = Settings()
```

Instantiating `Settings()` at module level means:
1. **Every import of `app`** (or `from app import ...`) triggers Pydantic settings validation
2. **Testing requires environment variables** to be set before import — the `conftest.py` `env` section in `pyproject.toml` handles this, but it's a fragile pattern
3. **Cannot re-initialize** settings with different values within the same process

---

### 🔹 `mypy` → `ty` transition completeness

| Removed | Added |
|---|---|
| `mypy >= 1.15.0` | `ty >= 0.0.15` |
| `mypy.ini` (file removed) | — |

`mypy` is static type checking; `ty` is **runtime** type checking. They serve different purposes. The `mypy.ini` was deleted and `make ty` replaced `mypy` in the `Makefile`, but it's unclear if `ty check` provides equivalent static analysis coverage. Consider running both for safety, or document why the change was sufficient.

---

### 🔹 Commit message typo

```
e085db9 cohre: updated python version to 3.14
```

`"cohre"` → `"chore"` 🎯

---

### 🔹 README is minimal

**File:** `README.md`

```markdown
# cache-service
Cache service based on FastAPI
```

The README lacks:
- Architecture overview
- Local development setup instructions
- API documentation / expected behavior
- Deployment instructions
- Environment variable documentation

---

### 🔹 `ujson` dependency removed

**File:** `pyproject.toml` (removed from main's dependencies)

`ujson>=5.10.0` was listed on `main` but is absent from the current `develop` branch. FastAPI uses `json.dumps` for serialization; without `ujson`, performance may degrade under high load. If removal was intentional, document the reasoning.

---

## ✨ Positive Observations

| Aspect | Details |
|---|---|
| ✅ **Clean layered architecture** | `api_handler → services → repositories` — clear separation of concerns |
| ✅ **Comprehensive test coverage** | Unit tests for repos & services + integration tests covering error/success paths |
| ✅ **Good exception handling** | Dedicated handlers for HTTP exceptions, validation errors, and generic errors |
| ✅ **Type hints throughout** | Full typing coverage across all application modules |
| ✅ **SSM for secrets** | API key stored in Parameter Store with decryption rather than env vars |
| ✅ **Dockerfile healthcheck** | `/health` endpoint has proper Docker HEALTHCHECK configuration |
| ✅ **Structured logging** | Powertools Logger with correlation ID support (once activated) and structured extras |
| ✅ **Terraform IaC** | Full infrastructure-as-code with proper IAM roles, DynamoDB TTL, and Lambda config |
| ✅ **Build artifact hashing** | Layer and function artifacts use SHA-256 for dedup |

---

## 📊 Summary

| Severity | Count |
|---|---|
| 🔴 Critical | 3 |
| 🟠 High | 7 |
| 🟡 Medium | 6 |
| 🟢 Low | 7 |
| **Total** | **23** |

**Top 3 recommendations:**
1. **Register `CorrelationIdMiddleware`** — it's already written, just not connected
2. **Add SSM retry/caching for `settings.api_key`** — cold start + external dependency = brittle
3. **Fix Django-style dual logging** — `logger.exception()` after `logger.warning()` doubles your log volume for expected errors
