"""
Shared FastAPI dependencies for the API layer.

Two concerns live here:

* **Service wiring** — a `get_*_service` factory builds each feature's
  service from request-scoped dependencies (a DB session, its repository
  port, a `UnitOfWork`). Routers depend on the `*Dep` alias, never construct
  a service by hand.

* **Authentication / authorization** — ``get_current_principal`` verifies the
  bearer token (if any) against TVM's JWKS (``core.security.verify_access_token``)
  and resolves it into a ``Principal``; ``require_role`` is a dependency
  factory that gates an endpoint at a minimum ``Role``. Every request resolves
  to either an authenticated principal backed by a valid TVM-issued access
  token, or the ``anonymous`` principal when no token is presented. A
  malformed, expired, or unverifiable token is rejected outright (401) rather
  than being downgraded to anonymous. Kumily never mints tokens or looks up a
  local user record — the token's claims are trusted as-is.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.ports.unit_of_work import UnitOfWork
from app.core.security import TokenError, verify_access_token
from app.db.database import get_session
from app.db.unit_of_work import SqlUnitOfWork
from app.features.etag.ports import EtagRepositoryPort
from app.features.etag.repository import EtagRepository
from app.features.guru_gita.ports import GuruGitaRepositoryPort
from app.features.guru_gita.repository import GuruGitaRepository
from app.features.guru_gita.service import GuruGitaService
from app.features.guruvani.ports import GuruvaniRepositoryPort
from app.features.guruvani.repository import GuruvaniRepository
from app.features.guruvani.service import GuruvaniService
from app.features.settings.ports import AppSettingRepositoryPort
from app.features.settings.repository import AppSettingRepository
from app.features.settings.service import SettingsService
from app.utils.roles import Role

SessionDep = Annotated[Session, Depends(get_session)]


# ── Service wiring ────────────────────────────────────────────────────────────
def get_unit_of_work(session: Annotated[Session, Depends(get_session)]) -> UnitOfWork:
    return SqlUnitOfWork(session)


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_etag_repository(session: SessionDep) -> EtagRepositoryPort:
    return EtagRepository(session)


EtagRepositoryDep = Annotated[EtagRepositoryPort, Depends(get_etag_repository)]


def get_guruvani_repository(session: SessionDep) -> GuruvaniRepositoryPort:
    return GuruvaniRepository(session)


GuruvaniRepositoryDep = Annotated[
    GuruvaniRepositoryPort, Depends(get_guruvani_repository)
]


def get_guruvani_service(
    guruvani_repository: GuruvaniRepositoryDep,
    unit_of_work: UnitOfWorkDep,
) -> GuruvaniService:
    return GuruvaniService(guruvani_repository, unit_of_work)


GuruvaniServiceDep = Annotated[GuruvaniService, Depends(get_guruvani_service)]


def get_guru_gita_repository(session: SessionDep) -> GuruGitaRepositoryPort:
    return GuruGitaRepository(session)


GuruGitaRepositoryDep = Annotated[
    GuruGitaRepositoryPort, Depends(get_guru_gita_repository)
]


def get_guru_gita_service(
    guru_gita_repository: GuruGitaRepositoryDep,
    unit_of_work: UnitOfWorkDep,
) -> GuruGitaService:
    return GuruGitaService(guru_gita_repository, unit_of_work)


GuruGitaServiceDep = Annotated[GuruGitaService, Depends(get_guru_gita_service)]


def get_settings_repository(session: SessionDep) -> AppSettingRepositoryPort:
    return AppSettingRepository(session)


SettingsRepositoryDep = Annotated[
    AppSettingRepositoryPort, Depends(get_settings_repository)
]


def get_settings_service(
    settings_repository: SettingsRepositoryDep,
    unit_of_work: UnitOfWorkDep,
) -> SettingsService:
    return SettingsService(settings_repository, unit_of_work)


SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]


# ── Principal ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Principal:
    """The authenticated (or anonymous) identity behind a request."""

    role: Role
    user_id: int | None = None

    @property
    def is_authenticated(self) -> bool:
        return self.role is not Role.ANONYMOUS


ANONYMOUS = Principal(role=Role.ANONYMOUS)

# auto_error=False so requests without an Authorization header are allowed
# through as the anonymous principal instead of being rejected here.
_bearer = HTTPBearer(auto_error=False)


def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    """
    Resolve the request's identity from its ``Authorization: Bearer`` access
    token, verified against TVM's JWKS.

    * No header → the anonymous principal.
    * A token that verifies against TVM's JWKS → that token's principal,
      trusted as-is (no local user lookup — Kumily owns no user data).
    * A malformed/expired/unverifiable token → 401.
    """
    if credentials is None:
        return ANONYMOUS

    try:
        claims = verify_access_token(credentials.credentials)
    except TokenError:
        raise _unauthorized("Invalid or expired token")

    return Principal(role=claims.role, user_id=claims.user_id)


def require_role(minimum: Role) -> Callable[..., Principal]:
    """
    Build a dependency that requires the caller to have at least *minimum* role.

    Returns the resolved ``Principal`` so handlers can read the current user.
    Anonymous callers hitting a protected endpoint get 401 (not authenticated);
    authenticated callers with an insufficient role get 403 (forbidden).
    """

    def dependency(
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> Principal:
        if principal.role.satisfies(minimum):
            return principal
        if not principal.is_authenticated:
            raise _unauthorized("Authentication required")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges for this resource",
        )

    return dependency


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
