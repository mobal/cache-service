# Cache Service

FastAPI-based caching service running on AWS Lambda with DynamoDB.

## Architecture

```
Client → API Gateway → Lambda (Mangum → FastAPI) → DynamoDB
                            │
                            └── SSM Parameter Store (API key)
```

- **FastAPI** — API framework with automatic OpenAPI docs
- **Mangum** — Adapts FastAPI for AWS Lambda + API Gateway
- **DynamoDB** — Key-value storage with TTL-based auto-expiry
- **SSM Parameter Store** — API key storage with encryption
- **Powertools** — Structured logging, observability
- **Terraform** — Infrastructure as Code (see `infrastructure/`)

## Development

### Prerequisites

- Python 3.14
- [uv](https://docs.astral.sh/uv/) package manager

### Setup

```bash
# Install dependencies
uv sync

# Install dev dependencies
uv sync --group dev

# Set up environment
cp .env.example .env
```

### Run tests

```bash
# Full test suite
make test

# Lint and format
make lint
make format

# Security scan
make bandit
```

### Run locally

```bash
uv run uvicorn app.api_handler:app --reload --port 3000
```

Open [http://localhost:3000/docs](http://localhost:3000/docs) for Swagger UI.

## API

### `GET /api/cache/{key}`

Retrieve a cached value by key.

**Headers:** `X-Api-Key: <your-api-key>`

**Response `200`:**
```json
{
  "key": "my-key",
  "value": "some-value",
  "createdAt": "2026-06-11T14:00:00+00:00",
  "ttl": 1750000000,
  "expiredAt": "2026-06-11T15:00:00+00:00"
}
```

**Response `404`:**
```json
{
  "status": 404,
  "id": "uuid",
  "message": "KeyValue was not found"
}
```

### `POST /api/cache`

Create or update a cached value.

**Headers:** `X-Api-Key: <your-api-key>`

**Request body:**
```json
{
  "key": "my-key",
  "value": "any JSON value",
  "ttl": 3600
}
```

- `ttl` — optional, time-to-live in seconds from now

**Response:** `201 Created`

### `GET /health`

Health check endpoint.

```json
{ "status": "healthy" }
```

## Deployment

### Build

```bash
# Build Lambda deployment package
make build-lambda

# Build Lambda layer with dependencies
make build-layer

# Build both
make build
```

### Infrastructure

Deploy with Terraform:

```bash
cd infrastructure
terraform init
terraform plan
terraform apply
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `APP_NAME` | Application name | `cache-service` |
| `STAGE` | Deployment stage | `local` |
| `DEBUG` | Enable debug mode | `true` |
| `DEFAULT_TIMEZONE` | Timezone for timestamps | `UTC` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CACHE_SERVICE_API_KEY_SSM_PARAM_NAME` | SSM param path for API key | `/dev/service/api-key` |
| `AWS_ACCESS_KEY_ID` | AWS access key | — |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | — |
| `AWS_DEFAULT_REGION` | AWS region | `eu-central-1` |
