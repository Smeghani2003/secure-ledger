"""PlaidService: thin wrapper over the Plaid Python client.

Keeps the rest of the app free of Plaid SDK imports and lets us mock easily
in tests.
"""

from __future__ import annotations

from plaid.api import plaid_api
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products

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
