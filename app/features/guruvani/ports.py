from abc import abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Protocol


class GuruvaniNotFoundException(Exception):
    """Raised when reading/deleting a quote (or one of its translations) that does not exist."""


@dataclass(frozen=True, kw_only=True)
class GuruvaniTranslation:
    language_code: str
    text: str


@dataclass(frozen=True, kw_only=True)
class GuruvaniGet:
    id: int
    sort_order: int
    translations: List[GuruvaniTranslation]


class GuruvaniRepositoryPort(Protocol):

    @abstractmethod
    def get(self, guruvani_id: int) -> Optional[GuruvaniGet]: ...

    @abstractmethod
    def list_all(self) -> List[GuruvaniGet]: ...

    @abstractmethod
    def get_random(self) -> Optional[GuruvaniGet]: ...

    @abstractmethod
    def create(self, sort_order: Optional[int]) -> GuruvaniGet: ...

    @abstractmethod
    def upsert_translation(
        self, guruvani_id: int, language_code: str, text: str
    ) -> GuruvaniGet: ...

    @abstractmethod
    def delete_translation(self, guruvani_id: int, language_code: str) -> None: ...

    @abstractmethod
    def update_sort_order(self, guruvani_id: int, sort_order: int) -> GuruvaniGet: ...

    @abstractmethod
    def delete(self, guruvani_id: int) -> None: ...
