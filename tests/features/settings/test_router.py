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


def test_list_is_public_and_returns_defaults(client):
    resp = client.get("/api/v1/settings")
    assert resp.status_code == 200
    keys = {row["key"] for row in resp.json()}
    assert keys == {"calendar_range", "languages"}


def test_get_unknown_key_returns_404(client):
    resp = client.get("/api/v1/settings/not-a-real-key")
    assert resp.status_code == 404


def test_get_known_key_without_a_stored_row_returns_default(client):
    resp = client.get("/api/v1/settings/languages")
    assert resp.status_code == 200
    body = resp.json()
    assert body["key"] == "languages"
    assert body["value"] == {"codes": ["en", "ml"]}


def test_update_requires_admin(client):
    resp = client.put(
        "/api/v1/settings/calendar_range",
        json={"value": {"start_year": 2010, "end_year": 2040}},
    )
    assert resp.status_code == 401


def test_update_rejects_insufficient_role(client):
    resp = client.put(
        "/api/v1/settings/calendar_range",
        json={"value": {"start_year": 2010, "end_year": 2040}},
        headers=bearer_header(Role.USER),
    )
    assert resp.status_code == 403


def test_admin_can_update_and_public_can_read_it_back(client):
    updated = client.put(
        "/api/v1/settings/calendar_range",
        json={"value": {"start_year": 2010, "end_year": 2040}},
        headers=bearer_header(Role.ADMIN),
    )
    assert updated.status_code == 200
    assert updated.json()["value"] == {"start_year": 2010, "end_year": 2040}

    fetched = client.get("/api/v1/settings/calendar_range")
    assert fetched.status_code == 200
    assert fetched.json()["value"] == {"start_year": 2010, "end_year": 2040}


def test_update_unknown_key_returns_404(client):
    resp = client.put(
        "/api/v1/settings/not-a-real-key",
        json={"value": {}},
        headers=bearer_header(Role.ADMIN),
    )
    assert resp.status_code == 404


def test_update_rejects_invalid_value_shape(client):
    resp = client.put(
        "/api/v1/settings/calendar_range",
        json={"value": {"start_year": "not-a-year"}},
        headers=bearer_header(Role.ADMIN),
    )
    assert resp.status_code == 400


def test_read_endpoint_rejects_invalid_bearer_token(client):
    resp = client.get(
        "/api/v1/settings", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401
