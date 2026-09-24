from app.features.guruvani.ports import GuruvaniTranslation
from app.features.guruvani.repository import GuruvaniRepository


def test_get_returns_none_for_missing_id(session):
    repo = GuruvaniRepository(session)

    assert repo.get(999) is None


def test_create_assigns_sort_order_when_omitted(session):
    repo = GuruvaniRepository(session)

    first = repo.create(None)
    second = repo.create(None)

    assert first.sort_order == 1
    assert second.sort_order == 2
    assert first.translations == []


def test_create_respects_explicit_sort_order(session):
    repo = GuruvaniRepository(session)

    quote = repo.create(42)

    assert quote.sort_order == 42


def test_list_all_orders_by_sort_order(session):
    repo = GuruvaniRepository(session)
    repo.create(3)
    repo.create(1)
    repo.create(2)

    quotes = repo.list_all()

    assert [q.sort_order for q in quotes] == [1, 2, 3]


def test_get_random_returns_none_when_empty(session):
    repo = GuruvaniRepository(session)

    assert repo.get_random() is None


def test_get_random_returns_an_existing_quote(session):
    repo = GuruvaniRepository(session)
    created = repo.create(None)

    quote = repo.get_random()

    assert quote is not None
    assert quote.id == created.id


def test_upsert_translation_creates_new_row(session):
    repo = GuruvaniRepository(session)
    created = repo.create(None)

    quote = repo.upsert_translation(created.id, "en", "a saying")

    assert quote.translations == [
        GuruvaniTranslation(language_code="en", text="a saying")
    ]


def test_upsert_translation_updates_existing_row(session):
    repo = GuruvaniRepository(session)
    created = repo.create(None)
    repo.upsert_translation(created.id, "en", "first version")

    updated = repo.upsert_translation(created.id, "en", "second version")

    assert len(updated.translations) == 1
    assert updated.translations[0].text == "second version"


def test_upsert_translation_accumulates_languages_on_same_quote(session):
    repo = GuruvaniRepository(session)
    created = repo.create(None)
    repo.upsert_translation(created.id, "en", "english text")

    quote = repo.upsert_translation(created.id, "ml", "malayalam text")

    codes = {t.language_code for t in quote.translations}
    assert codes == {"en", "ml"}


def test_delete_translation_removes_only_that_language(session):
    repo = GuruvaniRepository(session)
    created = repo.create(None)
    repo.upsert_translation(created.id, "en", "english text")
    repo.upsert_translation(created.id, "ml", "malayalam text")

    repo.delete_translation(created.id, "en")

    quote = repo.get(created.id)
    assert quote is not None
    assert [t.language_code for t in quote.translations] == ["ml"]


def test_update_sort_order(session):
    repo = GuruvaniRepository(session)
    created = repo.create(1)

    updated = repo.update_sort_order(created.id, 5)

    assert updated.sort_order == 5


def test_delete_removes_the_quote_and_its_translations(session):
    repo = GuruvaniRepository(session)
    created = repo.create(None)
    repo.upsert_translation(created.id, "en", "english text")

    repo.delete(created.id)

    assert repo.get(created.id) is None
