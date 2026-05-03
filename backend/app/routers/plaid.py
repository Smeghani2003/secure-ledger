"""Plaid router: link-token, public-token exchange, sync."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DBSession
from app.models.plaid_item import PlaidItem
from app.schemas.plaid import (
    ExchangeRequest,
    ExchangeResponse,
    LinkTokenResponse,
    SyncItemResult,
    SyncResponse,
)
from app.services.crypto_service import CryptoService
from app.services.plaid_service import PlaidService
from app.services.sync_service import SyncService

router = APIRouter(prefix="/api/plaid", tags=["plaid"])


@router.post("/link-token", response_model=LinkTokenResponse)
async def create_link_token(user: CurrentUser) -> LinkTokenResponse:
    try:
        result = PlaidService().create_link_token(str(user.id))
    except Exception as e:  # plaid SDK raises a variety of types
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Plaid error: {e}",
        ) from e
    return LinkTokenResponse(**result)


@router.post("/exchange", response_model=ExchangeResponse, status_code=status.HTTP_201_CREATED)
async def exchange_public_token(
    payload: ExchangeRequest,
    user: CurrentUser,
    db: DBSession,
) -> ExchangeResponse:
    try:
        result = PlaidService().exchange_public_token(payload.public_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Plaid error: {e}",
        ) from e

    encrypted = CryptoService().encrypt(result["access_token"])
    item = PlaidItem(
        user_id=user.id,
        item_id=result["item_id"],
        institution_id=payload.institution_id,
        institution_name=payload.institution_name,
        access_token_ciphertext=encrypted,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return ExchangeResponse(
        item_id=item.item_id,
        institution_name=item.institution_name,
    )


@router.post("/sync", response_model=SyncResponse)
async def sync_all_items(user: CurrentUser, db: DBSession) -> SyncResponse:
    """Pull accounts + transaction deltas for every linked bank.

    First call returns the historical window (Plaid sandbox: ~30 days).
    Subsequent calls only return what changed since the last sync, using
    the cursor stored on each plaid_item.
    """
    sync = SyncService(db)
    outcomes = await sync.sync_user(user.id)

    items = [
        SyncItemResult(
            plaid_item_id=str(o.plaid_item_id),
            institution_name=o.institution_name,
            accounts_upserted=o.accounts_upserted,
            transactions_added=o.transactions_added,
            transactions_modified=o.transactions_modified,
            transactions_removed=o.transactions_removed,
            last_synced_at=o.last_synced_at,
            error=o.error,
        )
        for o in outcomes
    ]
    return SyncResponse(
        items=items,
        total_accounts_upserted=sum(i.accounts_upserted for i in items),
        total_transactions_added=sum(i.transactions_added for i in items),
        total_transactions_modified=sum(i.transactions_modified for i in items),
        total_transactions_removed=sum(i.transactions_removed for i in items),
    )
