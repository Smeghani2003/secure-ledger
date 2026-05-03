"""Plaid-related request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LinkTokenResponse(BaseModel):
    link_token: str
    expiration: str


class ExchangeRequest(BaseModel):
    public_token: str
    institution_id: str | None = None
    institution_name: str | None = None


class ExchangeResponse(BaseModel):
    item_id: str
    institution_name: str | None


class SyncItemResult(BaseModel):
    plaid_item_id: str
    institution_name: str | None
    accounts_upserted: int
    transactions_added: int
    transactions_modified: int
    transactions_removed: int
    last_synced_at: datetime
    error: str | None = None


class SyncResponse(BaseModel):
    items: list[SyncItemResult]
    total_accounts_upserted: int
    total_transactions_added: int
    total_transactions_modified: int
    total_transactions_removed: int
