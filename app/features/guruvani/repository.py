"""
GuruvaniRepository — concrete adapter for ``GuruvaniRepositoryPort``, CRUD for
the ``guruvani_translation`` table against SQLModel.

A quote exists only as its ``GuruvaniTranslation`` rows: every row sharing a
``quote_id`` carries that quote's ``sort_order`` duplicated across languages,
with no separate parent table. Mutating methods do NOT commit — the caller
(``features.guruvani.service``) owns the transaction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlmodel import Session, select

from app.db.models.guruvani import GuruvaniTranslation as GuruvaniTranslationRow
from app.db.typing_utils import col
from app.features.guruvani.ports import GuruvaniGet, GuruvaniTranslation


@dataclass()
class GuruvaniRepository:
    _s: Session

    def _rows_to_guruvani_get(
        self, rows: List[GuruvaniTranslationRow]
    ) -> Optional[GuruvaniGet]:
        if not rows:
            return None
        return GuruvaniGet(
            id=rows[0].quote_id,
            sort_order=rows[0].sort_order,
            translations=[
                GuruvaniTranslation(language_code=row.language_code, text=row.text)
                for row in rows
            ],
        )

    def _rows_for(self, quote_id: int) -> List[GuruvaniTranslationRow]:
        return list(
            self._s.exec(
                select(GuruvaniTranslationRow)
                .where(col(GuruvaniTranslationRow.quote_id) == quote_id)
                .order_by(col(GuruvaniTranslationRow.language_code))
            ).all()
        )

    # ── Getters ────────────────────────────────────────────────────────────────

    def get(self, guruvani_id: int) -> Optional[GuruvaniGet]:
        return self._rows_to_guruvani_get(self._rows_for(guruvani_id))

    def list_all(self) -> List[GuruvaniGet]:
        rows = self._s.exec(
            select(GuruvaniTranslationRow)
            .order_by(
                col(GuruvaniTranslationRow.sort_order),
                col(GuruvaniTranslationRow.quote_id),
                col(GuruvaniTranslationRow.language_code),
            )
        ).all()
        grouped: Dict[int, List[GuruvaniTranslationRow]] = {}
        order: List[int] = []
        for row in rows:
            if row.quote_id not in grouped:
                grouped[row.quote_id] = []
                order.append(row.quote_id)
            grouped[row.quote_id].append(row)
        quotes = [self._rows_to_guruvani_get(grouped[quote_id]) for quote_id in order]
        return [quote for quote in quotes if quote is not None]

    def get_random(self) -> Optional[GuruvaniGet]:
        """One quote picked at random, or None if none exist.

        ``func.random()`` is the SQL standard name for this and works
        identically on both Postgres and SQLite (the test suite's engine).
        """
        quote_id = self._s.exec(
            select(col(GuruvaniTranslationRow.quote_id))
            .distinct()
            .order_by(func.random())
            .limit(1)
        ).first()
        if quote_id is None:
            return None
        return self.get(quote_id)

    # ── Setters ────────────────────────────────────────────────────────────────

    def create(
        self, sort_order: Optional[int], language_code: str, text: str
    ) -> GuruvaniGet:
        """Insert a new quote's first translation row. Does NOT commit."""
        quote_id = self._next_quote_id()
        row = GuruvaniTranslationRow(
            quote_id=quote_id,
            language_code=language_code,
            text=text,
            sort_order=sort_order if sort_order is not None else self._next_sort_order(),
        )
        self._s.add(row)
        self._s.flush()
        quote = self.get(quote_id)
        assert quote is not None
        return quote

    def upsert_translation(
        self, guruvani_id: int, language_code: str, text: str
    ) -> GuruvaniGet:
        """Create or update the row for *(guruvani_id, language_code)*. Does NOT commit."""
        existing_rows = self._rows_for(guruvani_id)
        assert existing_rows
        row = self._get_translation_row(guruvani_id, language_code)
        if row is None:
            row = GuruvaniTranslationRow(
                quote_id=guruvani_id,
                language_code=language_code,
                text=text,
                sort_order=existing_rows[0].sort_order,
            )
        else:
            row.text = text
        self._s.add(row)
        self._s.flush()

        quote = self.get(guruvani_id)
        assert quote is not None
        return quote

    def delete_translation(self, guruvani_id: int, language_code: str) -> None:
        row = self._get_translation_row(guruvani_id, language_code)
        assert row is not None
        self._s.delete(row)
        self._s.flush()

    def update_sort_order(self, guruvani_id: int, sort_order: int) -> GuruvaniGet:
        rows = self._rows_for(guruvani_id)
        assert rows
        for row in rows:
            row.sort_order = sort_order
            self._s.add(row)
        self._s.flush()
        quote = self.get(guruvani_id)
        assert quote is not None
        return quote

    def delete(self, guruvani_id: int) -> None:
        rows = self._rows_for(guruvani_id)
        assert rows
        for row in rows:
            self._s.delete(row)
        self._s.flush()

    # ── Private helpers ─────────────────────────────────────────────────────────

    def _get_translation_row(
        self, guruvani_id: int, language_code: str
    ) -> Optional[GuruvaniTranslationRow]:
        return self._s.exec(
            select(GuruvaniTranslationRow).where(
                col(GuruvaniTranslationRow.quote_id) == guruvani_id,
                col(GuruvaniTranslationRow.language_code) == language_code,
            )
        ).first()

    def _next_quote_id(self) -> int:
        current_max = self._s.exec(select(func.max(GuruvaniTranslationRow.quote_id))).first()
        return (current_max or 0) + 1

    def _next_sort_order(self) -> int:
        current_max = self._s.exec(select(func.max(GuruvaniTranslationRow.sort_order))).first()
        return (current_max or 0) + 1
