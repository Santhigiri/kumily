# CLAUDE.md — kumily

## Project Purpose

Kumily is a FastAPI content-delivery server for **Santhigiri Ashram** (Pothencode, Kerala, India). It owns editable, ashram-facing content that has nothing to do with astronomical computation — starting with **Guruvani** (bilingual quotes attributed to the Guru), with more content features to follow.

It exists to keep [`chandiroor`](../chandiroor) — the Ashram's Panchangam microservice — scoped to panchangam/astronomical data only. `chandiroor` used to own the `guruvani` table and its CRUD endpoints directly; that feature is being migrated here first, as the template for every content feature that follows. Kumily and chandiroor are sibling services: independent deployments, independent databases, sharing only the identity provider (TVM) both verify tokens against.

---

## Git Workflow

- **Always start from `develop`** — before any work, checkout or pull the latest `develop` branch.
- **All changes merge to `develop` only** — feature branches must be created from `develop` and PRs must target `develop`.
- **Never touch `main`** — do not commit to, push to, or merge into `main` directly. `main` is promoted to only by the project maintainers.
- **Keep the PR title and description in sync with the diff** — before merging a PR, re-check that its title and description still accurately describe the actual changes on the branch (commits are often added after the PR was opened). Update both if they've drifted before merging.

```bash
git checkout develop
git pull origin develop
git checkout -b feature/<your-feature-name>
# ... make changes ...
git push -u origin feature/<your-feature-name>
# Open PR targeting develop
```

---

## Architecture Overview

The codebase uses a **feature-based (vertical-slice) architecture** built on **ports and adapters**, with a hard separation between business logic and the API layer. This is a non-negotiable constraint, and matches `chandiroor`'s structure exactly so the two services stay easy to work across.

Each feature owns its own `ports.py`, `repository.py`, `service.py`, `router.py`, and `schemas.py` under `features/<name>/`. Only pieces that are genuinely shared across *multiple* features — the persistence layer (`db/`) and cross-cutting infrastructure (`core/`) — live outside a feature folder. There is no `services/` folder: every feature's service lives in that feature's own `service.py`.

Everything below lives under `app/` (the on-disk package root). Paths elsewhere in this document are given relative to `app/` unless a leading `app/` is shown.

```
kumily/
├── .importlinter                # import-linter contract enforcing db/ and core/ never import api/ or features/
└── app/
    ├── main.py                     # App factory: wires lifespan, CORS, routers
    ├── api/
    │   └── deps.py                 # Shared Depends: get_*_service, get_current_principal, require_role — also where every port gets bound to its concrete adapter
    ├── features/                   # One subpackage per feature — the HTTP boundary + orchestration for that feature
    │   ├── guruvani/                    # Bilingual quote CRUD — the reference feature; match its shape for every new one
    │   │   ├── ports.py       # GuruvaniRepositoryPort (Protocol) + DTOs (GuruvaniGet/Create/Update) + GuruvaniNotFoundException
    │   │   ├── repository.py  # GuruvaniRepository — concrete adapter implementing the port against SQLModel
    │   │   ├── router.py      # CRUD endpoints, mounted at /api/v1/guruvani
    │   │   ├── service.py     # GuruvaniService — depends on GuruvaniRepositoryPort + UnitOfWork, never the concrete adapter
    │   │   └── schemas.py     # Request/response schemas (HTTP boundary shape, distinct from ports.py's DTOs)
    │   └── etag/                        # Shared ETag/conditional-response helpers — a utility feature, not yet consumed by guruvani
    │       ├── ports.py       # EtagRepositoryPort (Protocol) — no DTO, the boundary value is a bare ETag string
    │       ├── repository.py  # EtagRepository — concrete adapter implementing the port against SQLModel (dataset_etag table)
    │       └── service.py     # compute_etag / etag_json_response / etag_text_response / conditional_json_response / invalidate —
    │                           # plain functions, not a class; every router/service that wants ETag-validated responses imports
    │                           # this module directly, parametrized by EtagRepositoryPort + UnitOfWork rather than by state.
    ├── db/                         # Postgres persistence layer (SQLModel)
    │   ├── database.py             # Engine (reads DATABASE_URL from env), session factory, init_db()
    │   ├── unit_of_work.py         # SqlUnitOfWork — the one concrete UnitOfWork adapter (see "Ports & adapters" below)
    │   ├── typing_utils.py         # col() — Pyright escape hatch for SQLModel class-attribute typing, see its docstring
    │   ├── alembic/                # Alembic migration environment (env.py reads DATABASE_URL the same way the app does)
    │   └── models/                 # SQLModel table definitions (guruvani.py, dataset_etag.py)
    ├── core/                        # Shared by every feature
    │   ├── config.py                # Settings singleton: DATABASE_URL, TVM_JWKS_URL/TVM_JWT_PUBLIC_KEY, CORS
    │   ├── security.py              # verify_access_token — TVM JWT verification, returns TvmClaims
    │   ├── jwks_client.py           # Fetches + caches TVM's JWKS by kid, refetches once on an unknown kid
    │   └── ports/
    │       └── unit_of_work.py     # UnitOfWork (Protocol) — the transaction boundary every feature's service depends on
    └── utils/
        ├── roles.py                 # Role enum — mirrors chandiroor's exactly, both verify tokens from the same TVM
        ├── etag.py                  # if_none_match_satisfied — RFC 9110 If-None-Match header matching
        └── content_hash.py          # stable_hash — deterministic sha256 over a JSON-native structure, used for ETags
```

### Why this structure exists

**`features/<name>/`** is a vertical slice: its `router.py` is the HTTP boundary (parses/validates params, obtains a service via FastAPI `Depends`, delegates to it, translates domain errors to HTTP status codes) and its `service.py` sits between the router and persistence, depending only on that feature's `ports.py` `Protocol` (never a concrete `db/` repository class) and `core/ports/unit_of_work.py::UnitOfWork`. A feature never imports another feature's `service.py`/`router.py`/`schemas.py` directly — a cross-feature dependency on another feature's stateful service goes through a `Protocol` in `core/ports/` instead (none exist yet, since there is only one stateful feature so far; add one there the moment a second feature needs to depend on `GuruvaniService`, following the `SettingsServicePort` pattern documented in chandiroor's `CLAUDE.md` if you need a concrete worked example).

**`db/`** is the Postgres persistence layer (SQLModel), untouched by feature boundaries because it may back more than one feature (e.g. `dataset_etag` is shared infrastructure, not owned by any one feature). The engine is built in `db/database.py` from a `DATABASE_URL` connection string read from the environment (a Neon Postgres URL, e.g. `postgresql://user:password@host/db?sslmode=require`) — no credentials are hardcoded. `db/database.py::init_db()` ensures the schema exists at startup (idempotent, a dev-convenience safety net); the authoritative way schema changes reach the database is Alembic (`alembic upgrade head`), run once per deploy, never by the running app.

**`core/`** holds cross-cutting infrastructure with no feature-specific business logic: `config.py` (settings), `security.py` + `jwks_client.py` (TVM JWT verification), and `ports/unit_of_work.py` (the one Protocol every migrated feature's service depends on for its transaction boundary).

**`utils/`** holds `roles.py` and small, dependency-free helpers (`etag.py`, `content_hash.py`) genuinely shared across features or consumed by `core/`/`db/` (which must not depend on `features/`).

### Ports & adapters

Every feature is built as **ports and adapters**: a feature's service depends only on an abstract `Protocol` describing what it needs from persistence, never on a concrete SQLModel repository class or another feature's concrete service class. `features/guruvani/` is the reference example — read it before adding another feature.

The pieces, using `features/guruvani/` as the reference:

- **`ports.py`** defines three things: the repository `Protocol` (`GuruvaniRepositoryPort`), frozen `@dataclass` DTOs for data crossing the boundary (`GuruvaniGet`/`Create`/`Update`), and any domain exceptions the port can raise (`GuruvaniNotFoundException`). Nothing in `ports.py` imports SQLModel or a session.
- **The adapter** (`features/guruvani/repository.py`) is a concrete class implementing the port against SQLModel: it takes a `Session`, and every method translates ORM rows to/from the port's DTOs.
- **`service.py`** is a frozen `@dataclass` (not a plain `__init__`) holding the port and a `UnitOfWork` (`core/ports/unit_of_work.py`) as fields — e.g. `GuruvaniService(guruvani_repository: GuruvaniRepositoryPort, uow: UnitOfWork)`. It imports the port's Protocol and DTOs, never the concrete adapter class or `Session`. Request-schema → DTO conversion (and the reverse, DTO → response-schema) happens inside `service.py` methods, not in the router.
- **`db/unit_of_work.py::SqlUnitOfWork`** is the one concrete `UnitOfWork` adapter, wrapping a `Session`. A mutation wraps the repository call(s) in `with self.uow as uow: ...; uow.commit()`.
- **`api/deps.py`** is where every concrete adapter gets bound to its port and injected — e.g. `get_guruvani_repository(session) -> GuruvaniRepositoryPort: return GuruvaniRepository(session)`, then `get_guruvani_service(guruvani_repository: GuruvaniRepositoryDep, ...) -> GuruvaniService`. A feature's `router.py` depends on the service factory from `api/deps.py`; it never constructs a concrete adapter or service by hand.

`features/etag/` is the one exception to "service.py is a class": it isn't a class-based service at all — it's the shared payload/ETag-compute module every future feature's router or service can call into directly, so its functions take `etag_repository: EtagRepositoryPort` and `unit_of_work: UnitOfWork` as plain parameters rather than holding them as fields. `features/etag/ports.py` has no DTO — the value crossing the boundary is a bare ETag string keyed by dataset name, so there is no row shape to translate.

Match this granularity exactly when adding a new feature — one `ports.py` per feature, one adapter class, no finer-grained ports (no separate read/write port classes, no per-method protocols).

### Versioning without a `v1/` directory

Versioning is applied externally: a feature's `router.py` declares only its feature-local prefix (e.g. `/guruvani`), and `main.py` mounts it with `app.include_router(router, prefix="/api/v1")`. To add a `v2` of one feature's endpoints, add `features/<name>/router_v2.py` alongside the existing `router.py` and mount it with `prefix="/api/v2"` in `main.py` — no directory reshuffle needed.

### Authentication & Authorization

Kumily is a **JWT resource server**, not an identity provider: it never mints tokens, hashes passwords, or stores user records. Identity comes from TVM, the Ashram's dedicated auth microservice — the exact same TVM instance `chandiroor` verifies against, so a token that authenticates a request to one service authenticates the same user to the other. Every request's `Authorization: Bearer` access token is verified locally against TVM's public key rather than by calling TVM synchronously. TVM signs access tokens with its own private key (RS256); Kumily only ever holds the public half.

Two ways to get that public half, in preference order:

1. **TVM's JWKS** (`GET <tvm>/.well-known/jwks.json`, `core.config.settings.tvm_jwks_url`) — the normal path. `core/security.py::verify_access_token` resolves the signing key by the token's `kid` header via `core/jwks_client.py`, which caches the fetched key set and refetches once on an unknown `kid` (picks up a TVM key rotation with no Kumily config change).
2. **A static fallback key** (`core.config.settings.tvm_jwt_public_key`, a PEM-encoded RSA public key) — used only when the JWKS path is unset or the fetch fails.

At least one of `TVM_JWKS_URL` / `TVM_JWT_PUBLIC_KEY` must be set (`core/config.py`'s `_require_a_verification_source` validator) — there is no way to verify a token with neither.

The role hierarchy is `anonymous` < `user` < `editor` < `admin` < `super_admin` < `root` (`utils/roles.py::Role`) — identical to chandiroor's, since both mirror TVM's own `Role` enum (member *names* must match the `role` claim TVM signs), with `anonymous` added locally for "no token presented".

- **`get_current_principal`** resolves the request's bearer token into a `Principal` (`role`, `user_id`) by calling `verify_access_token`. No token → the `anonymous` principal. A malformed/expired/unverifiable token → `401` (it is **not** downgraded to anonymous).
- **`require_role(minimum)`** is a dependency factory that gates an endpoint at a minimum role. Anonymous callers to a protected endpoint get `401`; authenticated callers with an insufficient role get `403`.
- **Public endpoints still declare a guard** — `guruvani`'s read endpoints depend on `require_role(Role.ANONYMOUS)`, which permits anonymous access but still validates (and rejects) any bearer token that *is* supplied.

There are no `/api/v1/auth/*` endpoints — login, signup, refresh, and user/profile management are TVM's responsibility, not Kumily's. `TVM_JWT_ISSUER`/`TVM_JWT_AUDIENCE` must match TVM's configured `jwt.issuer`/`jwt.audience`.

---

## Mandatory Conventions

Follow these rules without exception.

### Layer import boundaries

- Route handlers in `features/<name>/router.py` must only parse HTTP params and delegate to that feature's `service.py`. They must not call a `db/` repository directly.
- `db/` (models, `database.py`, `unit_of_work.py`) must not import from `api/` or `features/`. Enforced by the `layer-boundaries` contract in `.importlinter` (`uv run lint-imports`).
- `core/` must not import from `api/` or `features/`. Same contract.
- Pydantic models belong in a feature's own `schemas.py`. Do not define response models inside `core/` or `utils/`.
- A feature's `service.py` may import `db/` and `core/`. Other features must not import one feature's stateful `service.py` class, `router.py`, or `schemas.py` directly — a cross-feature dependency on another feature's stateful service goes through a `Protocol` in `core/ports/` instead, never a direct import of the concrete class. (The exception, as in chandiroor, is a module of free functions already parametrized by ports rather than by state — `features/etag/service.py` — which any feature may import directly.)
- A feature must not have its `service.py` or `router.py` import a concrete repository/adapter class, or another feature's concrete stateful service class, directly — depend on the port (`Protocol`) and get the concrete instance via `api/deps.py`.

### Business logic placement

- All domain/business logic for a feature lives in that feature's own `service.py`.
- No business logic may live inside a route handler.

### Adding a new content feature

1. Create `features/<name>/` with `ports.py`, `repository.py`, `service.py`, `router.py`, and `schemas.py`, following `features/guruvani/`'s shape exactly (see "Ports & adapters" above). Do not add endpoints to an existing feature's router unless they are closely related to that feature.
2. Add the table model(s) under `db/models/<name>.py` and register them in `db/models/__init__.py` (import order matters if there are FKs — lookup/parent tables first).
3. Generate an Alembic migration: `uv run alembic revision --autogenerate -m "add <name> table"`, review the generated script, then `uv run alembic upgrade head` against your local database.
4. Wire the concrete adapter to its port in `api/deps.py` — a `get_<name>_repository` returning the port type, and a `get_<name>_service` building the service from it + `UnitOfWorkDep`.
5. Register the new router in `main.py` using `app.include_router(router, prefix="/api/v1")`. Routers themselves should not hardcode the version segment (see "Versioning without a `v1/` directory" above).
6. **Choose an authorization level with `require_role`.** Public read endpoints use `require_role(Role.ANONYMOUS)` (permits anonymous, still validates any supplied token). Any endpoint that **mutates** state must be gated at the appropriate role — `require_role(Role.ADMIN)` for admin-only content writes, following `guruvani`'s pattern. Apply the guard per-endpoint via the decorator's `dependencies=[...]` when a router mixes privilege levels, or at the router level when they are uniform.
7. If the feature serves read-heavy, rarely-changing content, consider using `features/etag/service.py`'s `conditional_json_response`/`etag_json_response` helpers for cache-friendly reads — see their docstrings.
8. Add tests mirroring `tests/features/guruvani/` — repository round-trips (`test_repository.py`) + router CRUD and role-guard checks (`test_router.py`).

---

## Tech Stack

| Dependency | Purpose |
|---|---|
| `fastapi` | HTTP framework and request validation |
| `uvicorn[standard]` | ASGI server (uvloop/httptools for production) |
| `sqlmodel` | ORM / table definitions over SQLAlchemy for the persistence layer |
| `psycopg2-binary` | PostgreSQL driver (Neon) |
| `python-dotenv` | Loads `DATABASE_URL` from a local `.env` during development |
| `python-jose[cryptography]` | Verifies TVM-issued RS256 JWT access tokens against TVM's JWKS (`core/security.py`, `core/jwks_client.py`) |
| `requests` | Fetches TVM's JWKS over HTTP (`core/jwks_client.py`) |
| `pydantic-settings` | Typed settings (`DATABASE_URL`, `TVM_JWKS_URL`, ...) in `core/config.py` |
| `alembic` | Schema migrations against Postgres |

`pytest`, `httpx`, and `import-linter` (test/CI-only) live in the `dev` dependency group (`pyproject.toml`'s `[dependency-groups]`); the runtime image installs the main dependency set alone (`uv sync --no-dev`).

Dependency management is via **[uv](https://docs.astral.sh/uv/)**, not pip/venv — `uv.lock` is committed and is the source of truth for exact resolved versions. Use `uv add <package>` / `uv remove <package>` to change dependencies, never hand-edit `pyproject.toml`'s dependency lists and forget to run `uv lock`.

---

## Running the Project

### Local development

```bash
uv sync                # installs the full dependency set, including dev tools, into .venv
cp .env.example .env   # then fill in your Neon DATABASE_URL and TVM_JWKS_URL
uv run uvicorn app.main:app --reload --port 8001
```

`DATABASE_URL` must be set (in the environment or a local `.env`) or startup fails fast — it points at a Neon/Postgres database. Set `TVM_JWKS_URL` to TVM's JWKS endpoint, and/or `TVM_JWT_PUBLIC_KEY` as a static fallback — at least one is required, or the app fails fast at startup. See `.env.example` for the auth variables and their defaults.

Startup only ensures the schema exists (`init_db()`); it does not load any data or apply pending Alembic migrations. Run `uv run alembic upgrade head` to bring a fresh database up to the latest schema.

Kumily runs on port **8001** locally (chandiroor uses 8000), so both services can run side by side on one machine during the migration.

### Docker

```bash
docker build -t kumily .
docker run -p 8001:8001 kumily
```

The container exposes port 8001 and runs `uvicorn app.main:app --host 0.0.0.0 --port 8001`.

### Endpoints

Guruvani quotes (read public; writes require the `admin` role):

- `GET    /api/v1/guruvani` — list every quote, ordered by `sort_order` (public)
- `GET    /api/v1/guruvani/random` — fetch one quote at random (public)
- `GET    /api/v1/guruvani/{id}` — fetch one quote (public)
- `POST   /api/v1/guruvani` — create a quote (admin)
- `PUT    /api/v1/guruvani/{id}` — partial-update a quote (admin)
- `DELETE /api/v1/guruvani/{id}` — delete a quote (admin)

Authentication: Kumily has no `/api/v1/auth/*` endpoints of its own — it never issues tokens. Log in against TVM (the Ashram's auth microservice) and pass the resulting `Authorization: Bearer <token>` on every request to Kumily.

---

## Running Tests

```bash
uv run pytest tests/
```

`tests/` mirrors the `app/` layout: `tests/db/` for the shared persistence layer, `tests/features/<name>/` for a feature's repository/router tests, one test module per source module (e.g. `app/features/guruvani/repository.py` ↔ `tests/features/guruvani/test_repository.py`).

Current coverage:

- `tests/features/guruvani/test_repository.py` — `GuruvaniRepository` CRUD, sort-order assignment, random selection.
- `tests/features/guruvani/test_router.py` — end-to-end CRUD through `TestClient`, including admin-role enforcement and the `/random` route-ordering guard.
- `tests/features/etag/test_repository.py` — `EtagRepository` get/set/upsert round-trips.

Tests use an in-memory SQLite engine (the FK pragma listener in `app/db/database.py` makes SQLite behave closer to Postgres); see `tests/conftest.py`. The router tests override `get_session` onto a per-test session and drive the app with `TestClient`. `tests/conftest.py` also mints test bearer tokens for `require_role`-gated endpoints: `bearer_header(role, user_id=1)` returns an `Authorization` header carrying a throwaway RS256 token shaped like a real TVM-issued one, and the autouse `_mock_tvm_jwks` fixture points `core.jwks_client` at that same in-memory test keypair instead of making a real HTTP call — no real TVM instance is needed to run the suite.

---

## Database & Migrations

Kumily owns its **own** Postgres database, separate from chandiroor's — the two services do not share a database, only the TVM identity provider. `db/database.py::DATABASE_URL` points at it via the environment.

Schema changes are made through Alembic, not by hand-editing the database or relying on `init_db()`'s `create_all()` (which only creates missing tables and never alters an existing one — it exists purely as a local-dev safety net for `uvicorn --reload` before migrations have been run).

```bash
uv run alembic revision --autogenerate -m "describe the change"   # generate a migration after changing db/models/
uv run alembic upgrade head                                        # apply pending migrations
```

Review every autogenerated migration before committing it — `--autogenerate` is a starting point, not a guarantee of correctness (it can miss server-side defaults, check constraints, and some column-type changes).

The `guruvani` table's **data** has been migrated out of chandiroor's database into Kumily's own local Postgres instance (a one-time, separate operational step — a `pg_dump`/`pg_restore` of just that table, or a `COPY` via `psql` — not something either service's code handles). chandiroor's `/api/v1/guruvani/*` endpoints still exist as of this writing and are no longer the source of truth; removing chandiroor's guruvani feature entirely is a follow-up step, not yet done.

---

## Known Issues and Active Work

- The `guruvani` data has been migrated to Kumily's own Postgres — see "Database & Migrations" above. chandiroor's own `guruvani` feature/endpoints still exist and have not yet been removed; that cleanup is still pending.
- Kumily currently runs against a local Postgres instance on a Proxmox LXC container (`DATABASE_URL` in `.env`, not committed). Migrating this to Neon (matching chandiroor's setup) is still a follow-up step, not yet done.
- `features/etag/` is scaffolded but not yet wired into any `guruvani` endpoint — none of Kumily's current content is expensive enough to compute that a cached ETag matters yet. Wire it in (via `conditional_json_response`) when a future content feature actually needs cache-friendly reads.
- No CI deploy workflow exists yet (chandiroor's `.github/workflows/docker-build-push.yml` has no Kumily equivalent) — only `lint.yml` (import-linter) and `test.yml` (pytest) currently run in CI.

---

## What Not To Do

- Do not add a `services/` top-level folder — every feature's service lives in that feature's own `service.py`.
- Do not import another feature's concrete `service.py` class, `router.py`, or `schemas.py` directly from a different feature — go through a `Protocol` in `core/ports/`.
- Do not import `db/` or a concrete repository/adapter class from a feature's `router.py` — go through the feature's own `service.py`, wired via `api/deps.py`.
- Do not let `db/` or `core/` import from `api/` or `features/` — this is mechanically enforced by `.importlinter`, but don't rely on CI to catch it; check `uv run lint-imports` locally before pushing.
- Do not hand-edit `pyproject.toml`'s dependency lists without running `uv lock` afterward — `uv.lock` must always match `pyproject.toml`.
- Do not bypass Alembic for schema changes — `init_db()`'s `create_all()` is a dev-only safety net, not a migration tool.
- Do not treat chandiroor's and Kumily's `guruvani` data as synced — until the one-time data migration runs and chandiroor's guruvani feature is removed, they are independent copies.
