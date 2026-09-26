from app.features.settings.repository import AppSettingRepository


def test_get_returns_none_when_unset(session):
    repo = AppSettingRepository(session)

    assert repo.get("calendar_range") is None


def test_upsert_then_get_round_trips(session):
    repo = AppSettingRepository(session)

    repo.upsert("calendar_range", {"start_year": 2010, "end_year": 2040})
    session.commit()

    row = repo.get("calendar_range")
    assert row is not None
    assert row.key == "calendar_range"
    assert row.value == {"start_year": 2010, "end_year": 2040}


def test_upsert_is_an_upsert(session):
    repo = AppSettingRepository(session)

    repo.upsert("languages", {"codes": ["en"]})
    session.commit()
    repo.upsert("languages", {"codes": ["en", "ml"]})
    session.commit()

    assert repo.get("languages").value == {"codes": ["en", "ml"]}


def test_upsert_preserves_description_when_not_given(session):
    repo = AppSettingRepository(session)

    repo.upsert("languages", {"codes": ["en"]}, description="Available languages")
    session.commit()
    repo.upsert("languages", {"codes": ["en", "ml"]})
    session.commit()

    assert repo.get("languages").description == "Available languages"


def test_list_all_orders_by_key(session):
    repo = AppSettingRepository(session)

    repo.upsert("languages", {"codes": ["en"]})
    repo.upsert("calendar_range", {"start_year": 2000, "end_year": 2035})
    session.commit()

    assert [row.key for row in repo.list_all()] == ["calendar_range", "languages"]
