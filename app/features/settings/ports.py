from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Protocol


@dataclass(frozen=True, kw_only=True)
class AppSettingGet:
    key: str
    value: dict
    description: Optional[str] = None
    updated_at: datetime
    updated_by: Optional[int] = None


class AppSettingRepositoryPort(Protocol):

    @abstractmethod
    def get(self, key: str) -> Optional[AppSettingGet]: ...

    @abstractmethod
    def list_all(self) -> List[AppSettingGet]: ...

    @abstractmethod
    def upsert(
        self,
        key: str,
        value: dict,
        *,
        description: Optional[str] = None,
        updated_by: Optional[int] = None,
    ) -> AppSettingGet: ...
