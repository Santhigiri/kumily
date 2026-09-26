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
    resp = client.get("/api/v2/settings")
    assert resp.status_code == 200
    keys = {row["key"] for row in resp.json()}
    assert keys == {"calendar_range", "languages"}


def test_update_requires_admin(client):
    resp = client.put(
        "/api/v2/settings/calendar_range",
        json={"value": {"start_year": 2010, "end_year": 2040}},
    )
    assert resp.status_code == 401


def test_admin_write_on_v2_is_visible_on_v1(client):
    updated = client.put(
        "/api/v2/settings/languages",
        json={"value": {"codes": ["en"]}},
        headers=bearer_header(Role.ADMIN),
    )
    assert updated.status_code == 200

    fetched = client.get("/api/v1/settings/languages")
    assert fetched.status_code == 200
    assert fetched.json()["value"] == {"codes": ["en"]}
