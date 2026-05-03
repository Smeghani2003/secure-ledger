"""PlaidService: thin wrapper over the Plaid Python client.

Keeps the rest of the app free of Plaid SDK imports and lets us mock easily
in tests.
"""

from __future__ import annotations

from typing import Any

from plaid.api import plaid_api
from plaid.api_client import ApiClient
from plaid.configuration import Configuration
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_sync_request import TransactionsSyncRequest

from app.config import settings


def _plaid_host(env: str) -> str:
    return {
        "sandbox": "https://sandbox.plaid.com",
        "development": "https://development.plaid.com",
        "production": "https://production.plaid.com",
    }.get(env, "https://sandbox.plaid.com")


class PlaidService:
    def __init__(self) -> None:
        configuration = Configuration(
            host=_plaid_host(settings.PLAID_ENV),
            api_key={
                "clientId": settings.PLAID_CLIENT_ID,
                "secret": settings.PLAID_SECRET,
            },
        )
        self._client = plaid_api.PlaidApi(ApiClient(configuration))

    # ---------- Link / exchange ----------

    def create_link_token(self, user_id: str) -> dict[str, str]:
        req = LinkTokenCreateRequest(
            client_name="SecureLedger",
            language="en",
            country_codes=[CountryCode(c) for c in settings.plaid_country_codes_list],
            user=LinkTokenCreateRequestUser(client_user_id=user_id),
            products=[Products(p) for p in settings.plaid_products_list],
        )
        if settings.PLAID_REDIRECT_URI:
            req.redirect_uri = settings.PLAID_REDIRECT_URI
        resp = self._client.link_token_create(req)
        return {"link_token": resp["link_token"], "expiration": str(resp["expiration"])}

    def exchange_public_token(self, public_token: str) -> dict[str, str]:
        req = ItemPublicTokenExchangeRequest(public_token=public_token)
        resp = self._client.item_public_token_exchange(req)
        return {"access_token": resp["access_token"], "item_id": resp["item_id"]}

    # ---------- Sync ----------

    def get_accounts(self, access_token: str) -> list[dict[str, Any]]:
        """Return the current list of accounts (with balances) for an item.

        Each item is the raw Plaid account dict — caller is responsible for
        mapping it to our schema.
        """
        req = AccountsGetRequest(access_token=access_token)
        resp = self._client.accounts_get(req)
        return [a.to_dict() for a in resp["accounts"]]

    def transactions_sync(
        self, access_token: str, cursor: str | None
    ) -> dict[str, Any]:
        """Pull all transaction deltas since `cursor`, paginating internally.

        Returns a dict with keys: added, modified, removed, next_cursor.
        First call (cursor=None) returns the full historical window the
        institution exposes (sandbox: ~30 days).
        """
        added: list[dict[str, Any]] = []
        modified: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        current_cursor = cursor or ""

        while True:
            req = TransactionsSyncRequest(
                access_token=access_token,
                cursor=current_cursor,
            )
            resp = self._client.transactions_sync(req)
            added.extend(t.to_dict() for t in resp["added"])
            modified.extend(t.to_dict() for t in resp["modified"])
            removed.extend(t.to_dict() for t in resp["removed"])
            current_cursor = resp["next_cursor"]
            if not resp["has_more"]:
                break

        return {
            "added": added,
            "modified": modified,
            "removed": removed,
            "next_cursor": current_cursor,
        }
