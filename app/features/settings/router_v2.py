"""v2 of the public application config, mounted at ``/api/v2/settings``.

Scaffolded per CLAUDE.md's "Versioning without a `v1/` directory": a
feature-local ``router_v2.py`` alongside ``router.py``, mounted separately in
``main.py`` at ``prefix="/api/v2"`` — no directory reshuffle. Behavior
currently mirrors v1 exactly (same ``SettingsService``, same schemas); this
is the seam to diverge from v1 when a v2-only change is needed, without
touching v1's contract.

* ``GET /api/v2/settings``       — list every setting                        (public)
* ``GET /api/v2/settings/{key}`` — fetch one setting                          (public)
* ``PUT /api/v2/settings/{key}`` — replace a setting's value                  (admin)
"""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import Principal, SettingsServiceDep, get_current_principal, require_role
from app.features.etag.service import etag_json_response
from app.features.settings.schemas import AppSettingRead, AppSettingUpdate
from app.features.settings.service import InvalidSettingValue, SettingNotFound
from app.utils.roles import Role

router = APIRouter(prefix="/settings", tags=["settings-v2"])


@router.get(
    "",
    response_model=List[AppSettingRead],
    dependencies=[Depends(require_role(Role.ANONYMOUS))],
)
def list_settings(request: Request, service: SettingsServiceDep) -> Response:
    payload = [AppSettingRead.model_validate(row) for row in service.list_all()]
    return etag_json_response(request, payload)


@router.get(
    "/{key}",
    response_model=AppSettingRead,
    dependencies=[Depends(require_role(Role.ANONYMOUS))],
)
def get_setting(key: str, request: Request, service: SettingsServiceDep) -> Response:
    try:
        row = service.get_row(key)
    except SettingNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"Setting '{key}' not found."
        )
    payload = AppSettingRead.model_validate(row)
    return etag_json_response(request, payload)


@router.put(
    "/{key}",
    response_model=AppSettingRead,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
def update_setting(
    key: str,
    payload: AppSettingUpdate,
    service: SettingsServiceDep,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> AppSettingRead:
    try:
        row = service.update(key, payload, updated_by=principal.user_id)
    except SettingNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"Setting '{key}' not found."
        )
    except InvalidSettingValue as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return AppSettingRead.model_validate(row)
