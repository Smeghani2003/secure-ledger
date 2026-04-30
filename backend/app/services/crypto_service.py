"""CryptoService: Fernet-based at-rest encryption for sensitive tokens.

This is intentionally small. In production you would source FERNET_KEY from
KMS / Secrets Manager and rotate via the encryption_key_version column on
PlaidItem.
"""

from __future__ import annotations

from cryptography.fernet import Fernet

from app.config import settings


class CryptoService:
    def __init__(self, key: str | None = None) -> None:
        self._fernet = Fernet((key or settings.FERNET_KEY).encode())

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        return self._fernet.decrypt(ciphertext).decode()
