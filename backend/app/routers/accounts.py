"""Accounts router: list accounts owned by the current user."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.deps import CurrentUser, DBSession
from app.models.account import Account
from app.models.plaid_item import PlaidItem
from app.schemas.account import AccountResponse

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
async def list_accounts(user: CurrentUser, db: DBSession) -> list[Account]:
    stmt = (
        select(Account)
        .join(PlaidItem, PlaidItem.id == Account.plaid_item_id)
        .where(PlaidItem.user_id == user.id)
        .order_by(Account.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
