"""CRUD endpoints for Guru Gita verses.

* ``GET    /api/v1/guru-gita``                                        — list every verse, ordered by verse_number; every translation, or only ``?language_code=`` when given (public)
* ``GET    /api/v1/guru-gita/{verse_number}``                         — fetch one verse; every translation, or only ``?language_code=`` when given (public)
* ``PUT    /api/v1/guru-gita/{verse_number}/translations/{language}`` — create or update one language's text for a verse   (admin)
* ``DELETE /api/v1/guru-gita/{verse_number}/translations/{language}`` — remove one language's text for a verse              (admin)
* ``DELETE /api/v1/guru-gita/{verse_number}``                         — remove a verse entirely (every language)            (admin)

Reads are public (the anonymous principal is allowed, any supplied token is
still validated), writes require the ``admin`` role. Handlers stay thin:
parse the body, delegate to ``GuruGitaService``, and translate its domain
errors into HTTP status codes.

The list endpoint is ETag-validated via
``features.etag.service.conditional_json_response`` when no ``?language_code=``
filter is given: the ETag is persisted in the ``dataset_etag`` table (key
``"guru_gita:all"``) rather than recomputed on every request, since the full
101-verse payload is static and read-heavy. Every write invalidates that
stored ETag via ``features.etag.service.invalidate`` so it never lags the
data it validates. A filtered request (``?language_code=`` given) bypasses
the persisted cache and uses ``features.etag.service.etag_json_response``
instead, computing the (smaller, per-language) ETag fresh every time rather
than persisting one stored key per language.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.deps import EtagRepositoryDep, GuruGitaServiceDep, UnitOfWorkDep, require_role
from app.features.etag.service import conditional_json_response, etag_json_response, invalidate
from app.features.guru_gita.schemas import GuruGitaTranslationUpsert, GuruGitaVerseDetail
from app.features.guru_gita.service import GuruGitaVerseNotFound
from app.utils.languages import LanguageCode
from app.utils.roles import Role

router = APIRouter(prefix="/guru-gita", tags=["guru-gita"])

_ALL_KEY = "guru_gita:all"


@router.get(
    "",
    response_model=List[GuruGitaVerseDetail],
    dependencies=[Depends(require_role(Role.ANONYMOUS))],
)
def list_guru_gita(
    request: Request,
    service: GuruGitaServiceDep,
    etag_repository: EtagRepositoryDep,
    unit_of_work: UnitOfWorkDep,
    language_code: Optional[LanguageCode] = Query(default=None),
) -> Response:
    if language_code is None:
        return conditional_json_response(
            request, etag_repository, unit_of_work, _ALL_KEY, service.list_all
        )
    return etag_json_response(request, service.list_all(language_code.value))


@router.get(
    "/{verse_number}",
    response_model=GuruGitaVerseDetail,
    dependencies=[Depends(require_role(Role.ANONYMOUS))],
)
def get_guru_gita_verse(
    verse_number: int,
    service: GuruGitaServiceDep,
    language_code: Optional[LanguageCode] = Query(default=None),
) -> GuruGitaVerseDetail:
    try:
        value = language_code.value if language_code is not None else None
        return service.get(verse_number, value)
    except GuruGitaVerseNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"Verse '{verse_number}' not found."
        )


@router.put(
    "/{verse_number}/translations/{language_code}",
    response_model=GuruGitaVerseDetail,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
def upsert_guru_gita_translation(
    verse_number: int,
    language_code: LanguageCode,
    payload: GuruGitaTranslationUpsert,
    service: GuruGitaServiceDep,
    etag_repository: EtagRepositoryDep,
    unit_of_work: UnitOfWorkDep,
) -> GuruGitaVerseDetail:
    verse = service.upsert_translation(verse_number, language_code.value, payload.text)
    invalidate(etag_repository, unit_of_work, _ALL_KEY, service.list_all())
    return verse


@router.delete(
    "/{verse_number}/translations/{language_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
def delete_guru_gita_translation(
    verse_number: int,
    language_code: LanguageCode,
    service: GuruGitaServiceDep,
    etag_repository: EtagRepositoryDep,
    unit_of_work: UnitOfWorkDep,
) -> Response:
    try:
        service.delete_translation(verse_number, language_code.value)
    except GuruGitaVerseNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Translation '{language_code.value}' for verse '{verse_number}' not found.",
        )
    invalidate(etag_repository, unit_of_work, _ALL_KEY, service.list_all())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{verse_number}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
def delete_guru_gita_verse(
    verse_number: int,
    service: GuruGitaServiceDep,
    etag_repository: EtagRepositoryDep,
    unit_of_work: UnitOfWorkDep,
) -> Response:
    try:
        service.delete_verse(verse_number)
    except GuruGitaVerseNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"Verse '{verse_number}' not found."
        )
    invalidate(etag_repository, unit_of_work, _ALL_KEY, service.list_all())
    return Response(status_code=status.HTTP_204_NO_CONTENT)
