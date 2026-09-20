"""
Shared fixtures for the test suite.

The unit fixtures use a fresh in-memory SQLite database per test (``sqlite://``
with a ``StaticPool`` so every connection sees the same schema/data). Importing
``app.db.database`` registers its module-level ``PRAGMA foreign_keys = ON``
connect listener against the SQLAlchemy ``Engine`` class, so FK enforcement
behaves the same as it does in production.
"""
from __future__ import annotations

import datetime as _dt
import os

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# app.db.database now requires DATABASE_URL (Postgres/Neon) at import time.
# Tests build their own in-memory SQLite engines and never touch the
# module-level engine, so a throwaway value just satisfies the import — no
# real connection is ever opened against it. Must be set before importing
# app.db.database below.
os.environ.setdefault("DATABASE_URL", "sqlite://")

# core.config.Settings requires TVM_JWKS_URL at import time (there is no
# local fallback secret). Tests never make a real HTTP call to it — see
# `_mock_tvm_jwks` below, which patches the JWKS fetch to return an
# in-memory test keypair instead.
os.environ.setdefault("TVM_JWKS_URL", "http://tvm.invalid/.well-known/jwks.json")

# Importing app.db.database registers the shared "connect" pragma listener
# that turns foreign_keys ON for every SQLite connection, including our test
# engine.
import app.db.database  # noqa: F401
import app.db.models  # noqa: F401 — register every table on SQLModel.metadata

import app.core.jwks_client as jwks_client
from app.core.config import settings
from app.utils.roles import Role


# ── Engine / session fixtures ─────────────────────────────────────────────────

@pytest.fixture
def engine():
    """A fresh, isolated in-memory SQLite engine with the full schema created."""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    try:
        yield eng
    finally:
        SQLModel.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture
def session(engine):
    """A Session bound to the in-memory engine (schema only, no seed data)."""
    with Session(engine) as s:
        yield s


# ── TVM JWT test helpers ───────────────────────────────────────────────────────
#
# Kumily never mints tokens itself — it only verifies RS256 access tokens
# against TVM's JWKS (``app.core.jwks_client``). These helpers mint tokens
# shaped like a real TVM-issued one, signed with a throwaway in-memory test
# keypair, and patch the JWKS fetch so verification resolves against that same
# keypair instead of making a real HTTP call.

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk as _jose_jwk
from jose import jwt as _jose_jwt

_TEST_KID = "test-key-1"
_test_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_test_private_pem = _test_private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode("utf-8")
_test_public_pem = (
    _test_private_key.public_key()
    .public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    .decode("utf-8")
)
_test_public_jwk = _jose_jwk.construct(_test_public_pem, algorithm="RS256").to_dict()
_test_public_jwk["kid"] = _TEST_KID


def mint_tvm_token(role: Role, user_id: int = 1, is_verified: bool = True) -> str:
    """Mint a throwaway RS256 access token shaped like a real TVM-issued one."""
    claims = {
        "userId": user_id,
        "role": role.name,
        "isVerified": is_verified,
        "iss": settings.tvm_jwt_issuer,
        "aud": settings.tvm_jwt_audience,
        "exp": _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=1),
    }
    return _jose_jwt.encode(
        claims, _test_private_pem, algorithm="RS256", headers={"kid": _TEST_KID}
    )


def bearer_header(role: Role, user_id: int = 1) -> dict:
    """An ``Authorization`` header carrying a freshly minted test token."""
    return {"Authorization": f"Bearer {mint_tvm_token(role, user_id)}"}


@pytest.fixture(autouse=True)
def _mock_tvm_jwks(monkeypatch):
    """Resolve TVM's JWKS to the in-memory test keypair, never a real HTTP call."""
    monkeypatch.setattr(
        jwks_client, "_fetch_jwks", lambda: {_TEST_KID: _test_public_jwk}
    )
    jwks_client.reset_cache()
    yield
    jwks_client.reset_cache()
