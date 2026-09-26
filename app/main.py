from app.utils.startup_timing import IMPORT_STARTED_AT  # noqa: F401 — must be the first import; see that module's docstring

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.features.guru_gita.router import router as guru_gita_v1_router
from app.features.guruvani.router import router as guruvani_v1_router
from app.utils.lifespan import lifespan

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["ETag"],  # let browser JS read the ETag to send back in If-None-Match
)

app.include_router(guruvani_v1_router, prefix="/api/v1")
app.include_router(guru_gita_v1_router, prefix="/api/v1")
