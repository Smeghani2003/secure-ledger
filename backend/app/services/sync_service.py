"""SyncService: pulls accounts & transactions from Plaid into our DB.

The orchestration (decrypt token, call Plaid, upsert rows, save cursor)
lives here so the router stays a thin HTTP shell and the logic is easy
to unit-test by mocking PlaidService.

Plaid amount conventions:
- Plaid returns floats in dollars (e.g. 89.40)
- Positive = outflow (purchase, debit)
- Negative = inflow (deposit, refund)
We persist as integer cents preserving the same sign convention.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date as Date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.plaid_item import PlaidItem
from app.models.transaction import Transaction
from app.services.crypto_service import CryptoService
from app.services.plaid_service import PlaidService


@dataclass
class SyncItemOutcome:
    plaid_item_id: uuid.UUID
    institution_name: str | None
    accounts_upserted: int
    transactions_added: int
    transactions_modified: int
    transactions_removed: int
    last_synced_at: datetime
    error: str | None = None


def _to_cents(amount: float | int | None) -> int:
    if amount is None:
        return 0
    return int(round(float(amount) * 100))


def _parse_date(value: Any) -> Date | None:
    """Plaid returns dates as datetime.date already in v22+; defend anyway."""
    if value is None:
        return None
    if isinstance(value, Date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return Date.fromisoformat(value)
    return None


def _category_from_pfc(pfc: dict[str, Any] | None) -> str | None:
    """Pull the primary personal_finance_category if present."""
    if not pfc:
        return None
    primary = pfc.get("primary")
    return str(primary) if primary else None


class SyncService:
    def __init__(
        self,
        db: AsyncSession,
        plaid: PlaidService | None = None,
        crypto: CryptoService | None = None,
    ) -> None:
        self.db = db
        self.plaid = plaid or PlaidService()
        self.crypto = crypto or CryptoService()

    async def sync_plaid_item(self, item: PlaidItem) -> SyncItemOutcome:
        """Sync one linked bank: accounts + transactions delta."""
        try:
            access_token = self.crypto.decrypt(item.access_token_ciphertext)
        except Exception as e:
            return SyncItemOutcome(
                plaid_item_id=item.id,
                institution_name=item.institution_name,
                accounts_upserted=0,
                transactions_added=0,
                transactions_modified=0,
                transactions_removed=0,
                last_synced_at=datetime.now(UTC),
                error=f"decrypt failed: {e!s}",
            )

        accounts_upserted = 0
        added_count = 0
        modified_count = 0
        removed_count = 0

        try:
            # 1. Refresh accounts (creates new ones, updates balances on existing)
            plaid_accounts = self.plaid.get_accounts(access_token)
            plaid_account_id_to_local_id = await self._upsert_accounts(
                item.id, plaid_accounts
            )
            accounts_upserted = len(plaid_account_id_to_local_id)

            # 2. Pull transaction deltas using stored cursor
            sync_result = self.plaid.transactions_sync(
                access_token, item.transactions_cursor
            )

            added_count = await self._apply_added(
                sync_result["added"], plaid_account_id_to_local_id
            )
            modified_count = await self._apply_modified(
                sync_result["modified"], plaid_account_id_to_local_id
            )
            removed_count = await self._apply_removed(sync_result["removed"])

            # 3. Persist new cursor + bookkeeping
            item.transactions_cursor = sync_result["next_cursor"]
            item.last_synced_at = datetime.now(UTC)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            return SyncItemOutcome(
                plaid_item_id=item.id,
                institution_name=item.institution_name,
                accounts_upserted=0,
                transactions_added=0,
                transactions_modified=0,
                transactions_removed=0,
                last_synced_at=datetime.now(UTC),
                error=f"sync failed: {e!s}",
            )

        return SyncItemOutcome(
            plaid_item_id=item.id,
            institution_name=item.institution_name,
            accounts_upserted=accounts_upserted,
            transactions_added=added_count,
            transactions_modified=modified_count,
            transactions_removed=removed_count,
            last_synced_at=item.last_synced_at or datetime.now(UTC),
        )

    async def sync_user(self, user_id: uuid.UUID) -> list[SyncItemOutcome]:
        """Sync every active plaid_item belonging to the user."""
        result = await self.db.execute(
            select(PlaidItem).where(
                PlaidItem.user_id == user_id, PlaidItem.status == "active"
            )
        )
        items = list(result.scalars().all())
        outcomes: list[SyncItemOutcome] = []
        for item in items:
            outcomes.append(await self.sync_plaid_item(item))
        return outcomes

    # ---------- internals ----------

    async def _upsert_accounts(
        self, plaid_item_id: uuid.UUID, plaid_accounts: list[dict[str, Any]]
    ) -> dict[str, uuid.UUID]:
        """Insert new accounts, update balance/name on existing.

        Returns mapping of plaid_account_id -> our internal Account.id so the
        transaction loop can resolve foreign keys.
        """
        if not plaid_accounts:
            return {}

        plaid_ids = [a["account_id"] for a in plaid_accounts]
        existing_result = await self.db.execute(
            select(Account).where(Account.plaid_account_id.in_(plaid_ids))
        )
        existing_by_plaid_id = {
            a.plaid_account_id: a for a in existing_result.scalars().all()
        }

        mapping: dict[str, uuid.UUID] = {}
        for raw in plaid_accounts:
            balances = raw.get("balances") or {}
            currency = (
                balances.get("iso_currency_code")
                or balances.get("unofficial_currency_code")
                or "USD"
            )
            current_cents = _to_cents(balances.get("current"))
            available_cents = _to_cents(balances.get("available"))

            account = existing_by_plaid_id.get(raw["account_id"])
            if account is None:
                account = Account(
                    plaid_item_id=plaid_item_id,
                    plaid_account_id=raw["account_id"],
                    name=raw.get("name") or "Account",
                    official_name=raw.get("official_name"),
                    mask=raw.get("mask"),
                    type=str(raw.get("type") or "depository"),
                    subtype=(
                        str(raw["subtype"]) if raw.get("subtype") is not None else None
                    ),
                    currency=currency,
                    current_balance_cents=current_cents,
                    available_balance_cents=available_cents,
                )
                self.db.add(account)
                # flush so account.id is populated for the transaction FK
                await self.db.flush()
            else:
                account.name = raw.get("name") or account.name
                account.official_name = raw.get("official_name")
                account.mask = raw.get("mask")
                account.type = str(raw.get("type") or account.type)
                account.subtype = (
                    str(raw["subtype"]) if raw.get("subtype") is not None else None
                )
                account.currency = currency
                account.current_balance_cents = current_cents
                account.available_balance_cents = available_cents

            mapping[raw["account_id"]] = account.id

        return mapping

    async def _apply_added(
        self,
        added: list[dict[str, Any]],
        plaid_to_local_account: dict[str, uuid.UUID],
    ) -> int:
        if not added:
            return 0
        # Defensive: skip duplicates already in DB (e.g. a retry after a
        # half-applied sync)
        plaid_txn_ids = [t["transaction_id"] for t in added]
        existing = await self.db.execute(
            select(Transaction.plaid_transaction_id).where(
                Transaction.plaid_transaction_id.in_(plaid_txn_ids)
            )
        )
        already_present = {row[0] for row in existing.all()}

        count = 0
        for raw in added:
            if raw["transaction_id"] in already_present:
                continue
            account_local_id = plaid_to_local_account.get(raw["account_id"])
            if account_local_id is None:
                # Plaid returned a transaction for an account we didn't see in
                # /accounts/get — can happen briefly during institution updates.
                continue
            self.db.add(_transaction_from_plaid(raw, account_local_id))
            count += 1
        await self.db.flush()
        return count

    async def _apply_modified(
        self,
        modified: list[dict[str, Any]],
        plaid_to_local_account: dict[str, uuid.UUID],
    ) -> int:
        if not modified:
            return 0
        plaid_txn_ids = [t["transaction_id"] for t in modified]
        existing_result = await self.db.execute(
            select(Transaction).where(
                Transaction.plaid_transaction_id.in_(plaid_txn_ids)
            )
        )
        existing_by_plaid_id = {
            t.plaid_transaction_id: t for t in existing_result.scalars().all()
        }
        count = 0
        for raw in modified:
            existing = existing_by_plaid_id.get(raw["transaction_id"])
            account_local_id = plaid_to_local_account.get(raw["account_id"])
            if existing is None:
                # Plaid said "modified" but we don't have it — treat as added.
                if account_local_id is not None:
                    self.db.add(_transaction_from_plaid(raw, account_local_id))
                    count += 1
                continue
            _apply_plaid_to_transaction(existing, raw)
            count += 1
        await self.db.flush()
        return count

    async def _apply_removed(self, removed: list[dict[str, Any]]) -> int:
        if not removed:
            return 0
        plaid_txn_ids = [t["transaction_id"] for t in removed]
        result = await self.db.execute(
            select(Transaction).where(
                Transaction.plaid_transaction_id.in_(plaid_txn_ids)
            )
        )
        rows = list(result.scalars().all())
        for row in rows:
            await self.db.delete(row)
        await self.db.flush()
        return len(rows)


def _transaction_from_plaid(raw: dict[str, Any], account_id: uuid.UUID) -> Transaction:
    posted_date = _parse_date(raw.get("date")) or _parse_date(raw.get("authorized_date"))
    if posted_date is None:
        # Plaid should always return a date; fall back to today rather than crash.
        posted_date = datetime.now(UTC).date()
    return Transaction(
        account_id=account_id,
        plaid_transaction_id=raw["transaction_id"],
        amount_cents=_to_cents(raw.get("amount")),
        currency=raw.get("iso_currency_code") or "USD",
        posted_date=posted_date,
        authorized_date=_parse_date(raw.get("authorized_date")),
        name=raw.get("name") or "(unnamed)",
        merchant_name=raw.get("merchant_name"),
        category=_category_from_pfc(raw.get("personal_finance_category")),
        is_pending=bool(raw.get("pending", False)),
        raw_payload=_json_safe(raw),
    )


def _apply_plaid_to_transaction(t: Transaction, raw: dict[str, Any]) -> None:
    t.amount_cents = _to_cents(raw.get("amount"))
    t.currency = raw.get("iso_currency_code") or t.currency
    posted = _parse_date(raw.get("date")) or _parse_date(raw.get("authorized_date"))
    if posted is not None:
        t.posted_date = posted
    t.authorized_date = _parse_date(raw.get("authorized_date"))
    t.name = raw.get("name") or t.name
    t.merchant_name = raw.get("merchant_name")
    t.category = _category_from_pfc(raw.get("personal_finance_category"))
    t.is_pending = bool(raw.get("pending", False))
    t.raw_payload = _json_safe(raw)


def _json_safe(value: Any) -> Any:
    """Make a Plaid payload JSON-serializable for JSONB storage.

    Plaid SDK objects are dicts of dicts of primitives but some leaves are
    `datetime.date` / `datetime.datetime` which JSONB can't serialize.
    """
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, (datetime, Date)):
        return value.isoformat()
    return value
