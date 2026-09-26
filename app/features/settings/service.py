"""
SettingsService — CRUD for the admin-editable, publicly-readable
``app_setting`` table, plus typed getters other features' services can use.

Every typed getter falls back to a hardcoded default (see each per-key
Pydantic model in ``schemas.py``) when a key's row is absent, or (defensively)
if a stored value somehow fails validation — so a freshly-deployed database
with no ``app_setting`` rows yet still serves sane defaults.

Built the same way as ``GuruvaniService``: a frozen dataclass depending on
``AppSettingRepositoryPort`` (from ``features/settings/ports.py``) and a
``UnitOfWork``, never on the concrete adapter class.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.ports.unit_of_work import UnitOfWork
from app.features.settings.ports import AppSettingGet, AppSettingRepositoryPort
from app.features.settings.schemas import (
    AppSettingUpdate,
    CalendarRangeValue,
    LanguagesValue,
)
from app.utils.settings_keys import SettingKey

T = TypeVar("T", bound=BaseModel)

_VALUE_MODELS: Dict[SettingKey, Type[BaseModel]] = {
    SettingKey.CALENDAR_RANGE: CalendarRangeValue,
    SettingKey.LANGUAGES: LanguagesValue,
}


class SettingNotFound(Exception):
    """Raised when reading/updating a key name that isn't a known SettingKey."""


class InvalidSettingValue(Exception):
    """Raised when a PUT payload's ``value`` doesn't match the key's expected shape."""


@dataclass(frozen=True)
class SettingsService:
    app_setting_repository: AppSettingRepositoryPort
    uow: UnitOfWork

    # ── Generic CRUD (public reads, admin writes) ───────────────────────────

    def list_all(self) -> List[AppSettingGet]:
        """Every known ``SettingKey``, each as its stored row or (if absent)
        a synthesized default row — so a list always reflects every key
        currently in effect, even before any admin write has happened."""
        stored = {row.key: row for row in self.app_setting_repository.list_all()}
        return [
            stored.get(setting_key.value) or self._default_row(setting_key)
            for setting_key in SettingKey
        ]

    def get_row(self, key: str) -> AppSettingGet:
        try:
            setting_key = SettingKey(key)
        except ValueError as exc:
            raise SettingNotFound(key) from exc
        row = self.app_setting_repository.get(key)
        if row is not None:
            return row
        return self._default_row(setting_key)

    def update(
        self, key: str, payload: AppSettingUpdate, updated_by: Optional[int] = None
    ) -> AppSettingGet:
        """Validate *payload.value* against *key*'s shape and persist it.

        Unknown *key* -> :class:`SettingNotFound`. A shape mismatch ->
        :class:`InvalidSettingValue`. Commits.
        """
        try:
            setting_key = SettingKey(key)
        except ValueError as exc:
            raise SettingNotFound(key) from exc

        model = _VALUE_MODELS[setting_key]
        try:
            validated = model.model_validate(payload.value)
        except ValidationError as exc:
            raise InvalidSettingValue(str(exc)) from exc

        with self.uow as uow:
            row = self.app_setting_repository.upsert(
                key,
                validated.model_dump(),
                description=payload.description,
                updated_by=updated_by,
            )
            uow.commit()
            return row

    def _default_row(self, setting_key: SettingKey) -> AppSettingGet:
        model = _VALUE_MODELS[setting_key]
        return AppSettingGet(
            key=setting_key.value,
            value=model().model_dump(),
            description=None,
            updated_at=datetime.now(timezone.utc),
            updated_by=None,
        )

    # ── Typed getters (used by other features' services) ───────────────────

    def _value(self, key: SettingKey, model: Type[T]) -> T:
        row = self.app_setting_repository.get(key.value)
        if row is None:
            return model()
        try:
            return model.model_validate(row.value)
        except ValidationError:
            return model()

    def get_calendar_range(self) -> CalendarRangeValue:
        return self._value(SettingKey.CALENDAR_RANGE, CalendarRangeValue)

    def get_languages(self) -> LanguagesValue:
        return self._value(SettingKey.LANGUAGES, LanguagesValue)
