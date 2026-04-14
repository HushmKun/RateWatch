# RateWatch

RateWatch is a FastAPI service that fetches FX rates from multiple providers, normalizes a consensus value, caches live data in Redis, and stores historical snapshots in SQL.

## Prerequisites

- Python 3.14+
- Redis (required for runtime cache)
- Optional: Postgres (if you set `DATABASE_URL` to Postgres; default is SQLite)

## Local setup

1. Install dependencies:
   ```bash
   pip install -e ".[test]"
   ```
2. Start Redis (example with Docker):
   ```bash
   docker compose up -d redis
   ```
3. Run the API:
   ```bash
   python main.py
   ```

API base path: `/api/v1`

## Key endpoints

- `GET /api/v1/rates/{base}`
- `GET /api/v1/rates/{base}/{target}`
- `GET /api/v1/history/{pair}`
- `GET /api/v1/sources`

## Tests

- Full suite:
  ```bash
  pytest -q
  ```
- UTC normalization tests:
  ```bash
  pytest -q tests/unit/test_utc_handling.py
  ```

Note: current integration tests are placeholders and intentionally skipped unless a full Redis/Postgres stack is wired.

## Reliability and best-practice updates reflected in code

- **UTC normalization hardening**
  - `db/crud.py::_coerce_bucket` now normalizes bucket timestamps to UTC.
  - `cache/redis_client.py::_deserialize_rate` normalizes cached `normalized_at` timestamps to UTC.
  - Covered by `tests/unit/test_utc_handling.py`.

- **Input validation hardening**
  - `api/v1/routes/rates.py` catches malformed pair parsing and returns `INVALID_PAIR_FORMAT` instead of leaking `ValueError`.

- **Request logging improvement**
  - `main.py` request middleware now logs both successful responses and unhandled exceptions with request timing.

- **Async typing improvements**
  - Async wrapper callables use explicit typing (for example `Callable[..., Awaitable[...]]`) to make fetch/wrapper contracts clearer.

## Packaging, migration, and container defaults

- `pyproject.toml` now declares an explicit `build-system` and setuptools package list.
- `Dockerfile` uses `python:3.14-slim`, sets safer Python runtime env flags, and runs as a non-root `appuser`.
- `docker-compose.yml` uses safer Postgres password env syntax (`${POSTGRES_PASSWORD:-secret}`), tightened healthchecks, and an updated Redis image tag.
- `alembic.ini` includes `prepend_sys_path = .` and aligns the default SQLite URL with the app default.
- `alembic/versions/001_initial_schema.py` uses idempotent table/index creation flags where supported.
