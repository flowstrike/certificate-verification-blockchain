"""Phase 4: simple login + token auth for the local demo.

Confirmed Phase 0 decision 1 is email + password login for Admin and
Issuer. This module implements it in the smallest honest way:
- Issuer passwords are stored as PBKDF2-HMAC-SHA256 hashes (stdlib only,
  no extra dependency). Plaintext passwords are never stored.
- The Admin is a single account configured by environment variables
  (ADMIN_EMAIL / ADMIN_PASSWORD). Defaults below are LOCAL DEMO ONLY
  and must be overridden via env on any shared machine — same warning
  as the demo DATABASE_URL in config.py.
- Login returns a random token. Tokens live only in server memory
  (they do not survive a backend restart) and expire after 24 hours.
  This is a college-demo auth scheme, not production auth: there is no
  JWT, refresh, or password-reset flow, because the notes do not ask
  for any of those.

Student and Verifier have no login (confirmed decisions: student by
Certificate ID / QR, verifier public), so they need no token. Public
endpoints (record lookup, download, on-chain reads) stay public.
"""

import hashlib
import hmac
import os
import secrets
import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@demo.local")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
TOKEN_TTL_SECONDS = 24 * 60 * 60

# token -> {"role": "admin"|"issuer", "issuer_id": int|None, "expires": float}
_tokens: dict[str, dict] = {}

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, 200_000
    )
    return f"pbkdf2_sha256$200000${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        _algo, _iters, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), 200_000
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_token(role: str, issuer_id: int | None = None) -> str:
    token = secrets.token_urlsafe(32)
    _tokens[token] = {
        "role": role,
        "issuer_id": issuer_id,
        "expires": time.time() + TOKEN_TTL_SECONDS,
    }
    return token


def _current_user(
    credentials: HTTPAuthorizationCredentials | None,
) -> dict:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Login required")
    session = _tokens.get(credentials.credentials)
    if session is None or session["expires"] < time.time():
        if session is not None:
            _tokens.pop(credentials.credentials, None)
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return session


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    return _current_user(credentials)


def get_admin_user(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def get_issuer_user(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "issuer":
        raise HTTPException(status_code=403, detail="Issuer login required")
    return user
