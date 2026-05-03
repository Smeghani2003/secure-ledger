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
async def list_accounts(user: CurrentUser, db: DBSession) -> list[AccountResponse]:
    stmt = (
        select(Account, PlaidItem.institution_name, PlaidItem.last_synced_at)
        .join(PlaidItem, PlaidItem.id == Account.plaid_item_id)
        .where(PlaidItem.user_id == user.id)
        .order_by(Account.created_at.desc())
    )
    result = await db.execute(stmt)
    return [
        AccountResponse(
            id=account.id,
            name=account.name,
            official_name=account.official_name,
            mask=account.mask,
            type=account.type,
            subtype=account.subtype,
            currency=account.currency,
            current_balance_cents=account.current_balance_cents,
            available_balance_cents=account.available_balance_cents,
            institution_name=institution_name,
            last_synced_at=last_synced_at,
        )
        for account, institution_name, last_synced_at in result.all()
    ]
