"""CRUD endpoints for Guruvani quotes.

* ``GET    /api/v1/guruvani``                                     — list every quote, ordered by sort_order; every translation, or only ``?language_code=`` when given (public)
* ``GET    /api/v1/guruvani/random``                               — fetch one quote at random; every translation, or only ``?language_code=`` when given (public)
* ``GET    /api/v1/guruvani/{id}``                                 — fetch one quote; every translation, or only ``?language_code=`` when given (public)
* ``POST   /api/v1/guruvani``                                      — create a quote with its first translation (admin)
* ``PUT    /api/v1/guruvani/{id}/translations/{language_code}``    — create or update one language's text for a quote (admin)
* ``DELETE /api/v1/guruvani/{id}/translations/{language_code}``    — remove one language's text for a quote (admin)
* ``PUT    /api/v1/guruvani/{id}/sort-order``                      — update a quote's display order (admin)
* ``DELETE /api/v1/guruvani/{id}``                                 — delete a quote entirely (every language) (admin)

``/random`` is registered ahead of ``/{guruvani_id}`` so FastAPI's path
matching (first-match-wins, in declaration order) doesn't swallow the literal
"random" segment as an int path param.

Reads are public (the anonymous principal is allowed, any supplied token is
still validated), writes require the ``admin`` role. Handlers stay thin:
parse the body, delegate to ``GuruvaniService``, and translate its domain
errors into HTTP status codes.

The list endpoint is ETag-validated via ``features.etag.service.etag_json_response``
(the same fresh-computed-every-request approach ``features/settings/router.py``
uses): the ETag is hashed from the response on every request rather than
persisted, so a matching ``If-None-Match`` gets a ``304`` and a write is
reflected immediately with no separate invalidation step. Cheap enough for a
list this size — no need for the persisted-etag path the larger reference
datasets use.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.deps import GuruvaniServiceDep, require_role
from app.features.etag.service import etag_json_response
from app.features.guruvani.schemas import (
    GuruvaniCreate,
    GuruvaniDetail,
    GuruvaniSortOrderUpdate,
    GuruvaniTranslationUpsert,
)
from app.features.guruvani.service import GuruvaniNotFound
from app.utils.languages import LanguageCode
from app.utils.roles import Role

router = APIRouter(prefix="/guruvani", tags=["guruvani"])


@router.get(
    "",
    response_model=List[GuruvaniDetail],
    dependencies=[Depends(require_role(Role.ANONYMOUS))],
)
def list_guruvani(
    request: Request,
    service: GuruvaniServiceDep,
    language_code: Optional[LanguageCode] = Query(default=None),
) -> Response:
    value = language_code.value if language_code is not None else None
    return etag_json_response(request, service.list_all(value))


@router.get(
    "/random",
    response_model=GuruvaniDetail,
    dependencies=[Depends(require_role(Role.ANONYMOUS))],
)
def get_random_guruvani(
    service: GuruvaniServiceDep,
    language_code: Optional[LanguageCode] = Query(default=None),
) -> GuruvaniDetail:
    try:
        value = language_code.value if language_code is not None else None
        return service.get_random(value)
    except GuruvaniNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="No Guruvani entries exist."
        )


@router.get(
    "/{guruvani_id}",
    response_model=GuruvaniDetail,
    dependencies=[Depends(require_role(Role.ANONYMOUS))],
)
def get_guruvani(
    guruvani_id: int,
    service: GuruvaniServiceDep,
    language_code: Optional[LanguageCode] = Query(default=None),
) -> GuruvaniDetail:
    try:
        value = language_code.value if language_code is not None else None
        return service.get(guruvani_id, value)
    except GuruvaniNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"Guruvani '{guruvani_id}' not found."
        )


@router.post(
    "",
    response_model=GuruvaniDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
def create_guruvani(
    payload: GuruvaniCreate, service: GuruvaniServiceDep
) -> GuruvaniDetail:
    return service.create(payload.sort_order, payload.language_code.value, payload.text)


@router.put(
    "/{guruvani_id}/translations/{language_code}",
    response_model=GuruvaniDetail,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
def upsert_guruvani_translation(
    guruvani_id: int,
    language_code: LanguageCode,
    payload: GuruvaniTranslationUpsert,
    service: GuruvaniServiceDep,
) -> GuruvaniDetail:
    try:
        return service.upsert_translation(guruvani_id, language_code.value, payload.text)
    except GuruvaniNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"Guruvani '{guruvani_id}' not found."
        )


@router.delete(
    "/{guruvani_id}/translations/{language_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
def delete_guruvani_translation(
    guruvani_id: int, language_code: LanguageCode, service: GuruvaniServiceDep
) -> Response:
    try:
        service.delete_translation(guruvani_id, language_code.value)
    except GuruvaniNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Translation '{language_code.value}' for Guruvani '{guruvani_id}' not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{guruvani_id}/sort-order",
    response_model=GuruvaniDetail,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
def update_guruvani_sort_order(
    guruvani_id: int, payload: GuruvaniSortOrderUpdate, service: GuruvaniServiceDep
) -> GuruvaniDetail:
    try:
        return service.update_sort_order(guruvani_id, payload.sort_order)
    except GuruvaniNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"Guruvani '{guruvani_id}' not found."
        )


@router.delete(
    "/{guruvani_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
def delete_guruvani(guruvani_id: int, service: GuruvaniServiceDep) -> Response:
    try:
        service.delete(guruvani_id)
    except GuruvaniNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"Guruvani '{guruvani_id}' not found."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
