from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI

from app.db.database import init_db
from app.utils.startup_timing import IMPORT_STARTED_AT


@asynccontextmanager
async def lifespan(app: FastAPI):
    start = perf_counter()

    # Defensive safety net only — Alembic (`alembic upgrade head`, run once per
    # deploy, not by this process) is the authoritative way schema changes
    # reach the database. create_all() only creates *missing* tables and
    # never alters an existing one, so it's a harmless no-op once migrations
    # have run; it exists so a local `uvicorn --reload` dev flow that hasn't
    # run migrations yet still gets a usable schema.
    init_db()

    elapsed = perf_counter() - start
    print(f"Database ready in {elapsed:.3f}s")

    startup_elapsed = perf_counter() - IMPORT_STARTED_AT
    print(f"App startup took {startup_elapsed:.3f}s (import + schema check)")

    yield

    print("Shutdown")
