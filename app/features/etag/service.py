"""
ETag computation + conditional-response helpers.

Shared by every feature's router/service that wants ETag-validated JSON or
text responses. Both the read path (serve the body + its ETag) and any write
path that persists an ETag build on the same primitives here, so a stored
ETag can never disagree with the bytes an endpoint actually returns.
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.core.ports.unit_of_work import UnitOfWork
from app.features.etag.ports import EtagRepositoryPort
from app.utils.content_hash import stable_hash
from app.utils.etag import if_none_match_satisfied


def compute_etag(payload: Any) -> str:
    """Return a strong, quoted ETag for *payload* (a route-response object)."""
    return '"' + stable_hash(jsonable_encoder(payload)) + '"'


def etag_json_response(request: Request, payload: Any) -> Response:
    """
    Serve *payload* as an ETag-validated JSON response, computed fresh on every
    call — unlike :func:`conditional_json_response`, which persists the ETag to
    avoid rebuilding an expensive payload. Use this for payloads cheap enough
    to rebuild every request.
    """
    encoded = jsonable_encoder(payload)
    etag = '"' + stable_hash(encoded) + '"'

    if if_none_match_satisfied(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers={"ETag": etag})

    return JSONResponse(content=encoded, headers={"ETag": etag})


def etag_text_response(request: Request, text: str, media_type: str) -> Response:
    """
    Serve *text* (already-built) as an ETag-validated plain-text response,
    hashed fresh on every call.
    """
    etag = '"' + stable_hash(text) + '"'

    if if_none_match_satisfied(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers={"ETag": etag})

    return Response(content=text, media_type=media_type, headers={"ETag": etag})


def conditional_json_response(
    request: Request,
    etag_repository: EtagRepositoryPort,
    unit_of_work: UnitOfWork,
    key: str,
    payload_builder: Callable[[], Any],
) -> Response:
    """
    Serve an ETag-validated JSON response for the dataset stored under *key*.

    Returns ``304 Not Modified`` (no body, no payload build) when the client's
    ``If-None-Match`` matches the stored ETag — the cheap path for repeat polls.
    Otherwise builds the payload via *payload_builder* and returns it with its
    ``ETag`` header, computing and persisting the ETag on the way if it was not
    already stored.
    """
    etag = etag_repository.get(key)

    if etag and if_none_match_satisfied(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers={"ETag": etag})

    encoded = jsonable_encoder(payload_builder())
    if etag is None:
        etag = '"' + stable_hash(encoded) + '"'
        with unit_of_work as uow:
            etag_repository.set(key, etag)
            uow.commit()

    return JSONResponse(content=encoded, headers={"ETag": etag})


def invalidate(
    etag_repository: EtagRepositoryPort,
    unit_of_work: UnitOfWork,
    key: str,
    payload: Any,
) -> None:
    """
    Recompute and persist the ETag for *key* from *payload* — call this from a
    feature's mutation path (inside the same ``unit_of_work`` as the write) so
    a stored ETag never lags the data it validates. Commits.
    """
    with unit_of_work as uow:
        etag_repository.set(key, compute_etag(payload))
        uow.commit()
