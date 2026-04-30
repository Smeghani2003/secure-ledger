"""Plaid router: link-token, public-token exchange.

Sync of accounts/transactions arrives in Week 2 of the build plan; this
file leaves clear extension points.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DBSession
from app.models.plaid_item import PlaidItem
from app.schemas.plaid import ExchangeRequest, ExchangeResponse, LinkTokenResponse
from app.services.crypto_service import CryptoService
from app.services.plaid_service import PlaidService

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
