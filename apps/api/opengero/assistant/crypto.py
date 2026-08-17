from __future__ import annotations

import base64
import hashlib


def _fernet(secret: str):
    from cryptography.fernet import Fernet

    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def encrypt_secret(secret: str, plaintext: str) -> str:
    if not plaintext:
        return ""
    return _fernet(secret).encrypt(plaintext.encode()).decode()


def decrypt_secret(secret: str, token: str) -> str:
    if not token:
        return ""
    from cryptography.fernet import InvalidToken

    try:
        return _fernet(secret).decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return ""
