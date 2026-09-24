import pytest
from fastapi.testclient import TestClient

from app.db.database import get_session
from app.main import app
from app.utils.roles import Role
from tests.conftest import bearer_header


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_is_public(client):
    resp = client.get("/api/v1/guru-gita")
    assert resp.status_code == 200
    assert resp.json() == []


def test_upsert_translation_requires_admin(client):
    resp = client.put(
        "/api/v1/guru-gita/1/translations/en", json={"text": "verse one"}
    )
    assert resp.status_code == 401


def test_upsert_translation_rejects_insufficient_role(client):
    resp = client.put(
        "/api/v1/guru-gita/1/translations/en",
        json={"text": "verse one"},
        headers=bearer_header(Role.USER),
    )
    assert resp.status_code == 403


def test_admin_can_upsert_and_public_can_read_it_back(client):
    created = client.put(
        "/api/v1/guru-gita/1/translations/en",
        json={"text": "verse one"},
        headers=bearer_header(Role.ADMIN),
    )
    assert created.status_code == 200
    body = created.json()
    assert body["verse_number"] == 1
    assert body["translations"] == [{"language_code": "en", "text": "verse one"}]

    fetched = client.get("/api/v1/guru-gita/1")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_upsert_accumulates_multiple_languages(client):
    client.put(
        "/api/v1/guru-gita/1/translations/en",
        json={"text": "verse one"},
        headers=bearer_header(Role.ADMIN),
    )
    resp = client.put(
        "/api/v1/guru-gita/1/translations/ml",
        json={"text": "verse one ml"},
        headers=bearer_header(Role.ADMIN),
    )
    assert resp.status_code == 200
    codes = {t["language_code"] for t in resp.json()["translations"]}
    assert codes == {"en", "ml"}


def test_upsert_updates_existing_translation(client):
    client.put(
        "/api/v1/guru-gita/1/translations/en",
        json={"text": "draft"},
        headers=bearer_header(Role.ADMIN),
    )
    resp = client.put(
        "/api/v1/guru-gita/1/translations/en",
        json={"text": "final"},
        headers=bearer_header(Role.ADMIN),
    )
    assert resp.status_code == 200
    assert resp.json()["translations"] == [{"language_code": "en", "text": "final"}]


def test_get_missing_verse_returns_404(client):
    resp = client.get("/api/v1/guru-gita/999")
    assert resp.status_code == 404


def test_delete_translation_requires_admin(client):
    resp = client.delete("/api/v1/guru-gita/1/translations/en")
    assert resp.status_code == 401


def test_delete_missing_translation_returns_404(client):
    resp = client.delete(
        "/api/v1/guru-gita/1/translations/en", headers=bearer_header(Role.ADMIN)
    )
    assert resp.status_code == 404


def test_admin_can_delete_one_translation(client):
    client.put(
        "/api/v1/guru-gita/1/translations/en",
        json={"text": "verse one"},
        headers=bearer_header(Role.ADMIN),
    )
    client.put(
        "/api/v1/guru-gita/1/translations/ml",
        json={"text": "verse one ml"},
        headers=bearer_header(Role.ADMIN),
    )

    deleted = client.delete(
        "/api/v1/guru-gita/1/translations/en", headers=bearer_header(Role.ADMIN)
    )
    assert deleted.status_code == 204

    remaining = client.get("/api/v1/guru-gita/1").json()
    assert remaining["translations"] == [{"language_code": "ml", "text": "verse one ml"}]


def test_delete_missing_verse_returns_404(client):
    resp = client.delete("/api/v1/guru-gita/999", headers=bearer_header(Role.ADMIN))
    assert resp.status_code == 404


def test_admin_can_delete_entire_verse(client):
    client.put(
        "/api/v1/guru-gita/1/translations/en",
        json={"text": "verse one"},
        headers=bearer_header(Role.ADMIN),
    )
    client.put(
        "/api/v1/guru-gita/1/translations/ml",
        json={"text": "verse one ml"},
        headers=bearer_header(Role.ADMIN),
    )

    deleted = client.delete("/api/v1/guru-gita/1", headers=bearer_header(Role.ADMIN))
    assert deleted.status_code == 204

    assert client.get("/api/v1/guru-gita/1").status_code == 404


def test_list_supports_conditional_get_via_etag(client):
    client.put(
        "/api/v1/guru-gita/1/translations/en",
        json={"text": "verse one"},
        headers=bearer_header(Role.ADMIN),
    )

    first = client.get("/api/v1/guru-gita")
    etag = first.headers["etag"]

    cached = client.get("/api/v1/guru-gita", headers={"If-None-Match": etag})
    assert cached.status_code == 304

    client.put(
        "/api/v1/guru-gita/2/translations/en",
        json={"text": "verse two"},
        headers=bearer_header(Role.ADMIN),
    )
    after_write = client.get("/api/v1/guru-gita", headers={"If-None-Match": etag})
    assert after_write.status_code == 200


def test_list_filters_by_language_code(client):
    client.put(
        "/api/v1/guru-gita/1/translations/en",
        json={"text": "verse one"},
        headers=bearer_header(Role.ADMIN),
    )
    client.put(
        "/api/v1/guru-gita/1/translations/ml",
        json={"text": "verse one ml"},
        headers=bearer_header(Role.ADMIN),
    )

    resp = client.get("/api/v1/guru-gita", params={"language_code": "en"})
    assert resp.status_code == 200
    [verse] = resp.json()
    assert verse["translations"] == [{"language_code": "en", "text": "verse one"}]


def test_get_filters_by_language_code(client):
    client.put(
        "/api/v1/guru-gita/1/translations/en",
        json={"text": "verse one"},
        headers=bearer_header(Role.ADMIN),
    )
    client.put(
        "/api/v1/guru-gita/1/translations/ml",
        json={"text": "verse one ml"},
        headers=bearer_header(Role.ADMIN),
    )

    resp = client.get("/api/v1/guru-gita/1", params={"language_code": "ml"})
    assert resp.status_code == 200
    assert resp.json()["translations"] == [{"language_code": "ml", "text": "verse one ml"}]


def test_get_rejects_unsupported_language_code_filter(client):
    client.put(
        "/api/v1/guru-gita/1/translations/en",
        json={"text": "verse one"},
        headers=bearer_header(Role.ADMIN),
    )

    resp = client.get("/api/v1/guru-gita/1", params={"language_code": "fr"})
    assert resp.status_code == 422


def test_filtered_list_has_its_own_etag_not_the_persisted_all_etag(client):
    client.put(
        "/api/v1/guru-gita/1/translations/en",
        json={"text": "verse one"},
        headers=bearer_header(Role.ADMIN),
    )
    client.put(
        "/api/v1/guru-gita/1/translations/ml",
        json={"text": "verse one ml"},
        headers=bearer_header(Role.ADMIN),
    )

    all_resp = client.get("/api/v1/guru-gita")
    filtered_resp = client.get("/api/v1/guru-gita", params={"language_code": "en"})
    assert filtered_resp.status_code == 200
    assert filtered_resp.headers["etag"] != all_resp.headers["etag"]

    cached = client.get(
        "/api/v1/guru-gita",
        params={"language_code": "en"},
        headers={"If-None-Match": filtered_resp.headers["etag"]},
    )
    assert cached.status_code == 304


def test_read_endpoint_rejects_invalid_bearer_token(client):
    resp = client.get(
        "/api/v1/guru-gita", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401
