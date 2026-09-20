from app.features.etag.repository import EtagRepository


def test_get_returns_none_when_unset(session):
    repo = EtagRepository(session)

    assert repo.get("guruvani:all") is None


def test_set_then_get_round_trips(session):
    repo = EtagRepository(session)

    repo.set("guruvani:all", '"abc123"')
    session.commit()

    assert repo.get("guruvani:all") == '"abc123"'


def test_set_is_an_upsert(session):
    repo = EtagRepository(session)

    repo.set("guruvani:all", '"first"')
    session.commit()
    repo.set("guruvani:all", '"second"')
    session.commit()

    assert repo.get("guruvani:all") == '"second"'
