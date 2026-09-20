# Kumily

A FastAPI content-delivery server for **Santhigiri Ashram**. Owns editable, ashram-facing content — starting with **Guruvani** (bilingual quotes) — so that `chandiroor` (the Panchangam microservice) can stay focused on panchangam/astronomical data alone.

## Project layout

```
app/
├── main.py                # App factory: wires lifespan, CORS, and routers
├── api/deps.py            # Shared auth/DI dependencies (get_*_service, require_role, ...)
├── features/               # One subpackage per feature: ports.py + repository.py + service.py + router.py + schemas.py
│   ├── guruvani/            # Bilingual quote CRUD (public reads, admin writes)
│   └── etag/                 # Shared ETag/conditional-response helpers for future cacheable content endpoints
├── core/
│   ├── config.py            # Settings (DATABASE_URL, TVM_JWKS_URL, CORS, ...)
│   ├── security.py          # TVM-issued JWT verification
│   ├── jwks_client.py        # TVM JWKS fetch + cache
│   └── ports/                # Cross-feature Protocols (UnitOfWork, ...)
├── db/                     # Postgres persistence layer (SQLModel models + unit of work)
└── utils/                  # Cross-feature enums and helpers (roles, etag, content_hash, ...)
```

See `CLAUDE.md` for the full architecture reference, including layer import boundaries, the ports & adapters pattern, and per-feature conventions.

## Running locally

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env   # then fill in your Neon DATABASE_URL and TVM_JWKS_URL
uv run uvicorn app.main:app --reload --port 8001
```

`DATABASE_URL` must be set or startup fails fast. Startup only ensures the Postgres schema exists (`init_db()`) — schema changes are applied via Alembic migrations (`uv run alembic upgrade head`), not by the app itself. The server is then available at `http://localhost:8001`.

### With Docker

```bash
docker build -t kumily .
docker run -p 8001:8001 kumily
```

## Endpoints

Interactive API docs are available at `http://localhost:8001/docs`.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/guruvani` | public | List every quote, ordered by `sort_order` |
| `GET` | `/api/v1/guruvani/random` | public | Fetch one quote at random |
| `GET` | `/api/v1/guruvani/{id}` | public | Fetch one quote |
| `POST` | `/api/v1/guruvani` | admin | Create a quote |
| `PUT` | `/api/v1/guruvani/{id}` | admin | Partial-update a quote |
| `DELETE` | `/api/v1/guruvani/{id}` | admin | Delete a quote |

Auth: Kumily has no endpoints of its own for login/signup — it verifies `Authorization: Bearer <token>` access tokens minted by TVM, the same identity provider `chandiroor` trusts.

See `CLAUDE.md` for the full architecture reference.

## Running tests

```bash
uv run pytest tests/
```

## Tech stack

FastAPI · Uvicorn · SQLModel · Alembic · Postgres (Neon) · python-jose (TVM JWT verification)
