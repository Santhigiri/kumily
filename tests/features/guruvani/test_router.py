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
    resp = client.get("/api/v1/guruvani")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_requires_admin(client):
    resp = client.post("/api/v1/guruvani", json={})
    assert resp.status_code == 401


def test_create_rejects_insufficient_role(client):
    resp = client.post(
        "/api/v1/guruvani", json={}, headers=bearer_header(Role.USER)
    )
    assert resp.status_code == 403


def test_admin_can_create_and_public_can_read_it_back(client):
    created = client.post(
        "/api/v1/guruvani", json={}, headers=bearer_header(Role.ADMIN)
    )
    assert created.status_code == 201
    body = created.json()
    assert body["sort_order"] == 1
    assert body["translations"] == []

    fetched = client.get(f"/api/v1/guruvani/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_get_missing_returns_404(client):
    resp = client.get("/api/v1/guruvani/999")
    assert resp.status_code == 404


def test_random_returns_404_when_empty(client):
    resp = client.get("/api/v1/guruvani/random")
    assert resp.status_code == 404


def test_random_is_registered_ahead_of_id_route(client):
    client.post("/api/v1/guruvani", json={}, headers=bearer_header(Role.ADMIN))
    resp = client.get("/api/v1/guruvani/random")
    assert resp.status_code == 200
    assert resp.json()["sort_order"] == 1


def test_upsert_translation_requires_admin(client):
    created = client.post(
        "/api/v1/guruvani", json={}, headers=bearer_header(Role.ADMIN)
    ).json()

    resp = client.put(
        f"/api/v1/guruvani/{created['id']}/translations/en", json={"text": "a saying"}
    )
    assert resp.status_code == 401


def test_upsert_translation_rejects_insufficient_role(client):
    created = client.post(
        "/api/v1/guruvani", json={}, headers=bearer_header(Role.ADMIN)
    ).json()

    resp = client.put(
        f"/api/v1/guruvani/{created['id']}/translations/en",
        json={"text": "a saying"},
        headers=bearer_header(Role.USER),
    )
    assert resp.status_code == 403


def test_upsert_translation_rejects_unsupported_language_code(client):
    created = client.post(
        "/api/v1/guruvani", json={}, headers=bearer_header(Role.ADMIN)
    ).json()

    resp = client.put(
        f"/api/v1/guruvani/{created['id']}/translations/fr",
        json={"text": "a saying"},
        headers=bearer_header(Role.ADMIN),
    )
    assert resp.status_code == 422


def test_admin_can_upsert_and_public_can_read_it_back(client):
    created = client.post(
        "/api/v1/guruvani", json={}, headers=bearer_header(Role.ADMIN)
    ).json()

    resp = client.put(
        f"/api/v1/guruvani/{created['id']}/translations/en",
        json={"text": "a saying"},
        headers=bearer_header(Role.ADMIN),
    )
    assert resp.status_code == 200
    assert resp.json()["translations"] == [{"language_code": "en", "text": "a saying"}]

    fetched = client.get(f"/api/v1/guruvani/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == resp.json()


def test_upsert_accumulates_multiple_languages(client):
    created = client.post(
        "/api/v1/guruvani", json={}, headers=bearer_header(Role.ADMIN)
    ).json()
    client.put(
        f"/api/v1/guruvani/{created['id']}/translations/en",
        json={"text": "a saying"},
        headers=bearer_header(Role.ADMIN),
    )

    resp = client.put(
        f"/api/v1/guruvani/{created['id']}/translations/ml",
        json={"text": "a saying ml"},
        headers=bearer_header(Role.ADMIN),
    )
    assert resp.status_code == 200
    codes = {t["language_code"] for t in resp.json()["translations"]}
    assert codes == {"en", "ml"}


def test_upsert_translation_missing_quote_returns_404(client):
    resp = client.put(
        "/api/v1/guruvani/999/translations/en",
        json={"text": "a saying"},
        headers=bearer_header(Role.ADMIN),
    )
    assert resp.status_code == 404


def test_delete_translation_requires_admin(client):
    created = client.post(
        "/api/v1/guruvani", json={}, headers=bearer_header(Role.ADMIN)
    ).json()

    resp = client.delete(f"/api/v1/guruvani/{created['id']}/translations/en")
    assert resp.status_code == 401


def test_delete_missing_translation_returns_404(client):
    created = client.post(
        "/api/v1/guruvani", json={}, headers=bearer_header(Role.ADMIN)
    ).json()

    resp = client.delete(
        f"/api/v1/guruvani/{created['id']}/translations/en",
        headers=bearer_header(Role.ADMIN),
    )
    assert resp.status_code == 404


def test_admin_can_delete_one_translation(client):
    created = client.post(
        "/api/v1/guruvani", json={}, headers=bearer_header(Role.ADMIN)
    ).json()
    client.put(
        f"/api/v1/guruvani/{created['id']}/translations/en",
        json={"text": "a saying"},
        headers=bearer_header(Role.ADMIN),
    )
    client.put(
        f"/api/v1/guruvani/{created['id']}/translations/ml",
        json={"text": "a saying ml"},
        headers=bearer_header(Role.ADMIN),
    )

    deleted = client.delete(
        f"/api/v1/guruvani/{created['id']}/translations/en",
        headers=bearer_header(Role.ADMIN),
    )
    assert deleted.status_code == 204

    remaining = client.get(f"/api/v1/guruvani/{created['id']}").json()
    assert remaining["translations"] == [{"language_code": "ml", "text": "a saying ml"}]


def test_admin_can_update_sort_order(client):
    created = client.post(
        "/api/v1/guruvani", json={}, headers=bearer_header(Role.ADMIN)
    ).json()

    updated = client.put(
        f"/api/v1/guruvani/{created['id']}/sort-order",
        json={"sort_order": 5},
        headers=bearer_header(Role.ADMIN),
    )
    assert updated.status_code == 200
    assert updated.json()["sort_order"] == 5


def test_update_sort_order_missing_returns_404(client):
    resp = client.put(
        "/api/v1/guruvani/999/sort-order",
        json={"sort_order": 5},
        headers=bearer_header(Role.ADMIN),
    )
    assert resp.status_code == 404


def test_admin_can_delete(client):
    created = client.post(
        "/api/v1/guruvani", json={}, headers=bearer_header(Role.ADMIN)
    ).json()

    deleted = client.delete(
        f"/api/v1/guruvani/{created['id']}", headers=bearer_header(Role.ADMIN)
    )
    assert deleted.status_code == 204

    assert client.get(f"/api/v1/guruvani/{created['id']}").status_code == 404


def test_delete_missing_returns_404(client):
    resp = client.delete("/api/v1/guruvani/999", headers=bearer_header(Role.ADMIN))
    assert resp.status_code == 404


def test_read_endpoint_rejects_invalid_bearer_token(client):
    resp = client.get(
        "/api/v1/guruvani", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401
