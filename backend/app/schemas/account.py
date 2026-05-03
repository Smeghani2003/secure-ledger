"""Account/transaction read schemas."""

from __future__ import annotations

import uuid
from datetime import date as Date, datetime

from pydantic import BaseModel


class AccountResponse(BaseModel):
    id: uuid.UUID
    name: str
    official_name: str | None
    mask: str | None
    type: str
    subtype: str | None
    currency: str
    current_balance_cents: int | None
    available_balance_cents: int | None
    institution_name: str | None
    last_synced_at: datetime | None


class TransactionResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    amount_cents: int
    currency: str
    posted_date: Date
    name: str
    merchant_name: str | None
    category: str | None
    is_pending: bool

    model_config = {"from_attributes": True}
