from app.features.guru_gita.ports import GuruGitaTranslation
from app.features.guru_gita.repository import GuruGitaRepository


def test_get_returns_none_for_missing_verse(session):
    repo = GuruGitaRepository(session)

    assert repo.get(1) is None


def test_upsert_translation_creates_new_row(session):
    repo = GuruGitaRepository(session)

    verse = repo.upsert_translation(1, "en", "In the beginning...")

    assert verse.verse_number == 1
    assert verse.translations == [
        GuruGitaTranslation(language_code="en", text="In the beginning...")
    ]


def test_upsert_translation_updates_existing_row(session):
    repo = GuruGitaRepository(session)
    repo.upsert_translation(1, "en", "first version")

    updated = repo.upsert_translation(1, "en", "second version")

    assert len(updated.translations) == 1
    assert updated.translations[0].text == "second version"


def test_upsert_translation_accumulates_languages_on_same_verse(session):
    repo = GuruGitaRepository(session)
    repo.upsert_translation(1, "en", "english text")

    verse = repo.upsert_translation(1, "ml", "malayalam text")

    codes = {t.language_code for t in verse.translations}
    assert codes == {"en", "ml"}


def test_list_all_orders_by_verse_number(session):
    repo = GuruGitaRepository(session)
    repo.upsert_translation(3, "en", "third")
    repo.upsert_translation(1, "en", "first")
    repo.upsert_translation(2, "en", "second")

    verses = repo.list_all()

    assert [v.verse_number for v in verses] == [1, 2, 3]


def test_list_all_groups_translations_under_one_verse(session):
    repo = GuruGitaRepository(session)
    repo.upsert_translation(1, "en", "english text")
    repo.upsert_translation(1, "ml", "malayalam text")
    repo.upsert_translation(2, "en", "other verse")

    verses = repo.list_all()

    assert len(verses) == 2
    first = next(v for v in verses if v.verse_number == 1)
    assert {t.language_code for t in first.translations} == {"en", "ml"}


def test_delete_translation_removes_only_that_language(session):
    repo = GuruGitaRepository(session)
    repo.upsert_translation(1, "en", "english text")
    repo.upsert_translation(1, "ml", "malayalam text")

    repo.delete_translation(1, "en")

    verse = repo.get(1)
    assert verse is not None
    assert [t.language_code for t in verse.translations] == ["ml"]


def test_delete_verse_removes_every_language(session):
    repo = GuruGitaRepository(session)
    repo.upsert_translation(1, "en", "english text")
    repo.upsert_translation(1, "ml", "malayalam text")

    repo.delete_verse(1)

    assert repo.get(1) is None
