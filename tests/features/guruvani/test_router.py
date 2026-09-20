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
    resp = client.post(
        "/api/v1/guruvani", json={"text_en": "a", "text_ml": "a-ml"}
    )
    assert resp.status_code == 401


def test_create_rejects_insufficient_role(client):
    resp = client.post(
        "/api/v1/guruvani",
        json={"text_en": "a", "text_ml": "a-ml"},
        headers=bearer_header(Role.USER),
    )
    assert resp.status_code == 403


def test_admin_can_create_and_public_can_read_it_back(client):
    created = client.post(
        "/api/v1/guruvani",
        json={"text_en": "a", "text_ml": "a-ml"},
        headers=bearer_header(Role.ADMIN),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["text_en"] == "a"
    assert body["sort_order"] == 1

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
    client.post(
        "/api/v1/guruvani",
        json={"text_en": "a", "text_ml": "a-ml"},
        headers=bearer_header(Role.ADMIN),
    )
    resp = client.get("/api/v1/guruvani/random")
    assert resp.status_code == 200
    assert resp.json()["text_en"] == "a"


def test_admin_can_update(client):
    created = client.post(
        "/api/v1/guruvani",
        json={"text_en": "a", "text_ml": "a-ml"},
        headers=bearer_header(Role.ADMIN),
    ).json()

    updated = client.put(
        f"/api/v1/guruvani/{created['id']}",
        json={"text_en": "a-updated"},
        headers=bearer_header(Role.ADMIN),
    )
    assert updated.status_code == 200
    assert updated.json()["text_en"] == "a-updated"
    assert updated.json()["text_ml"] == "a-ml"


def test_update_missing_returns_404(client):
    resp = client.put(
        "/api/v1/guruvani/999",
        json={"text_en": "a"},
        headers=bearer_header(Role.ADMIN),
    )
    assert resp.status_code == 404


def test_admin_can_delete(client):
    created = client.post(
        "/api/v1/guruvani",
        json={"text_en": "a", "text_ml": "a-ml"},
        headers=bearer_header(Role.ADMIN),
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
