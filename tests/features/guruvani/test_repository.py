from app.features.guruvani.ports import GuruvaniCreate, GuruvaniUpdate
from app.features.guruvani.repository import GuruvaniRepository


def test_create_assigns_sort_order_when_omitted(session):
    repo = GuruvaniRepository(session)

    first = repo.create(GuruvaniCreate(text_en="a", text_ml="a-ml"))
    second = repo.create(GuruvaniCreate(text_en="b", text_ml="b-ml"))

    assert first.sort_order == 1
    assert second.sort_order == 2


def test_create_respects_explicit_sort_order(session):
    repo = GuruvaniRepository(session)

    row = repo.create(GuruvaniCreate(text_en="a", text_ml="a-ml", sort_order=42))

    assert row.sort_order == 42


def test_get_returns_none_for_missing_id(session):
    repo = GuruvaniRepository(session)

    assert repo.get(999) is None


def test_list_all_orders_by_sort_order(session):
    repo = GuruvaniRepository(session)
    repo.create(GuruvaniCreate(text_en="third", text_ml="m", sort_order=3))
    repo.create(GuruvaniCreate(text_en="first", text_ml="m", sort_order=1))
    repo.create(GuruvaniCreate(text_en="second", text_ml="m", sort_order=2))

    rows = repo.list_all()

    assert [r.text_en for r in rows] == ["first", "second", "third"]


def test_get_random_returns_none_when_empty(session):
    repo = GuruvaniRepository(session)

    assert repo.get_random() is None


def test_get_random_returns_an_existing_row(session):
    repo = GuruvaniRepository(session)
    created = repo.create(GuruvaniCreate(text_en="a", text_ml="a-ml"))

    row = repo.get_random()

    assert row is not None
    assert row.id == created.id


def test_update_applies_only_provided_fields(session):
    repo = GuruvaniRepository(session)
    created = repo.create(GuruvaniCreate(text_en="a", text_ml="a-ml", sort_order=1))

    updated = repo.update(created.id, GuruvaniUpdate(text_en="a2"))

    assert updated.text_en == "a2"
    assert updated.text_ml == "a-ml"
    assert updated.sort_order == 1


def test_delete_removes_the_row(session):
    repo = GuruvaniRepository(session)
    created = repo.create(GuruvaniCreate(text_en="a", text_ml="a-ml"))

    repo.delete(created.id)

    assert repo.get(created.id) is None
