"""Public application-wide config, mounted at ``/api/v1/settings``.

* ``GET /api/v1/settings``       — list every setting                        (public)
* ``GET /api/v1/settings/{key}`` — fetch one setting                          (public)
* ``PUT /api/v1/settings/{key}`` — replace a setting's value                  (admin)

Unlike an internal ops knob, these are ashram-facing client config
(calendar range, supported languages, ...) meant to be read by every caller,
authenticated or not — see ``utils.settings_keys.SettingKey`` for the known
keys and ``schemas.py`` for each key's expected ``value`` shape.

Reads are public (the anonymous principal is allowed, any supplied token is
still validated); only the write endpoint requires the ``admin`` role.
Both GET endpoints are ETag-validated via
``features.etag.service.etag_json_response``, computed fresh from the
response on every request — cheap enough a payload that there's no benefit
to the persisted-ETag path.
"""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import Principal, SettingsServiceDep, get_current_principal, require_role
from app.features.etag.service import etag_json_response
from app.features.settings.schemas import AppSettingRead, AppSettingUpdate
from app.features.settings.service import InvalidSettingValue, SettingNotFound
from app.utils.roles import Role

router = APIRouter(prefix="/settings", tags=["settings"])


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
