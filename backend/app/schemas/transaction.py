"""Transaction & spending schemas."""

from __future__ import annotations

import uuid
from datetime import date as Date

from pydantic import BaseModel


class TransactionItem(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    account_name: str
    amount_cents: int  # positive = outflow, negative = inflow (Plaid convention)
    currency: str
    posted_date: Date
    name: str
    merchant_name: str | None
    category: str | None
    is_pending: bool


class TransactionsListResponse(BaseModel):
    items: list[TransactionItem]
    total: int
    offset: int
    limit: int


class CategorySpend(BaseModel):
    category: str
    total_cents: int
    count: int


class SpendingResponse(BaseModel):
    days: int
    start_date: Date
    end_date: Date
    by_category: list[CategorySpend]
    total_cents: int
