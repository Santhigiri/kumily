from abc import abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Protocol


class GuruGitaVerseNotFoundException(Exception):
    """Raised when reading/deleting a verse (or one of its translations) that does not exist."""


@dataclass(frozen=True, kw_only=True)
class GuruGitaTranslation:
    language_code: str
    text: str


@dataclass(frozen=True, kw_only=True)
class GuruGitaVerseGet:
    verse_number: int
    translations: List[GuruGitaTranslation]


class GuruGitaRepositoryPort(Protocol):

    @abstractmethod
    def get(self, verse_number: int) -> Optional[GuruGitaVerseGet]: ...

    @abstractmethod
    def list_all(self) -> List[GuruGitaVerseGet]: ...

    @abstractmethod
    def upsert_translation(
        self, verse_number: int, language_code: str, text: str
    ) -> GuruGitaVerseGet: ...

    @abstractmethod
    def delete_translation(self, verse_number: int, language_code: str) -> None: ...

    @abstractmethod
    def delete_verse(self, verse_number: int) -> None: ...
