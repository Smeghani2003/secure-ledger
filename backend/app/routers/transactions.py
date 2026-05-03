"""Transactions router: list + spending-by-category aggregation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.deps import CurrentUser, DBSession
from app.models.account import Account
from app.models.plaid_item import PlaidItem
from app.models.transaction import Transaction
from app.schemas.transaction import (
    CategorySpend,
    SpendingResponse,
    TransactionItem,
    TransactionsListResponse,
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=TransactionsListResponse)
async def list_transactions(
    user: CurrentUser,
    db: DBSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    account_id: uuid.UUID | None = None,
    days: int | None = Query(None, ge=1, le=365),
) -> TransactionsListResponse:
    filters = [PlaidItem.user_id == user.id]
    if account_id is not None:
        filters.append(Transaction.account_id == account_id)
    if days is not None:
        cutoff = (datetime.now(UTC) - timedelta(days=days)).date()
        filters.append(Transaction.posted_date >= cutoff)

    count_stmt = (
        select(func.count(Transaction.id))
        .join(Account, Account.id == Transaction.account_id)
        .join(PlaidItem, PlaidItem.id == Account.plaid_item_id)
        .where(*filters)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    items_stmt = (
        select(Transaction, Account.name)
        .join(Account, Account.id == Transaction.account_id)
        .join(PlaidItem, PlaidItem.id == Account.plaid_item_id)
        .where(*filters)
        .order_by(
            Transaction.posted_date.desc(),
            Transaction.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(items_stmt)).all()

    items = [
        TransactionItem(
            id=t.id,
            account_id=t.account_id,
            account_name=account_name,
            amount_cents=t.amount_cents,
            currency=t.currency,
            posted_date=t.posted_date,
            name=t.name,
            merchant_name=t.merchant_name,
            category=t.category,
            is_pending=t.is_pending,
        )
        for t, account_name in rows
    ]
    return TransactionsListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/spending", response_model=SpendingResponse)
async def spending_by_category(
    user: CurrentUser,
    db: DBSession,
    days: int = Query(30, ge=1, le=365),
) -> SpendingResponse:
    """Sum of outflow (positive amounts) grouped by category, last N days.

    Excludes pending transactions and inflows (negative amounts). Returns
    categories sorted by total spend descending. Uncategorized transactions
    are bucketed under 'OTHER'.
    """
    end_date = datetime.now(UTC).date()
    start_date = end_date - timedelta(days=days)

    category_expr = func.coalesce(Transaction.category, "OTHER")
    stmt = (
        select(
            category_expr.label("category"),
            func.sum(Transaction.amount_cents).label("total_cents"),
            func.count(Transaction.id).label("count"),
        )
        .join(Account, Account.id == Transaction.account_id)
        .join(PlaidItem, PlaidItem.id == Account.plaid_item_id)
        .where(
            PlaidItem.user_id == user.id,
            Transaction.posted_date >= start_date,
            Transaction.posted_date <= end_date,
            Transaction.amount_cents > 0,
            Transaction.is_pending.is_(False),
        )
        .group_by(category_expr)
        .order_by(func.sum(Transaction.amount_cents).desc())
    )
    rows = (await db.execute(stmt)).all()

    by_category = [
        CategorySpend(
            category=row.category,
            total_cents=int(row.total_cents),
            count=int(row.count),
        )
        for row in rows
    ]
    total_cents = sum(c.total_cents for c in by_category)

    return SpendingResponse(
        days=days,
        start_date=start_date,
        end_date=end_date,
        by_category=by_category,
        total_cents=total_cents,
    )
