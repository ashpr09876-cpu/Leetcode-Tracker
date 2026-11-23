import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

_ph = PasswordHasher()
ALGO = "HS256"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return _ph.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: int) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "type": "access", "iat": now,
               "exp": now + timedelta(minutes=s.access_token_minutes)}
    return jwt.encode(payload, s.secret_key, algorithm=ALGO)


def decode_access_token(token: str) -> int | None:
    try:
        data = jwt.decode(token, get_settings().secret_key, algorithms=[ALGO])
        if data.get("type") != "access":
            return None
        return int(data["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def new_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_state_token(purpose: str, minutes: int = 10) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode({"purpose": purpose, "n": secrets.token_urlsafe(16), "exp": now + timedelta(minutes=minutes)},
                      s.secret_key, algorithm=ALGO)


def verify_state_token(token: str, purpose: str) -> bool:
    try:
        return jwt.decode(token, get_settings().secret_key, algorithms=[ALGO]).get("purpose") == purpose
    except jwt.PyJWTError:
        return False
