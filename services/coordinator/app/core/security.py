"""Password hashing (scrypt, stdlib — ADR-006) and JWT tokens (PyJWT)."""
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt as pyjwt

_SCRYPT_N = 2 ** 15
_SCRYPT_R = 8
_SCRYPT_P = 1
_DKLEN = 32
_MAXMEM = 64 * 1024 * 1024  # n=2^15, r=8 needs ~32 MiB; raise OpenSSL maxmem above default


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_DKLEN,
        maxmem=_MAXMEM,
    )
    return f"scrypt${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_hex, dk_hex = stored.split("$")
        if algo != "scrypt":
            return False
        dk = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
            dklen=_DKLEN,
            maxmem=_MAXMEM,
        )
        return hmac.compare_digest(dk.hex(), dk_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, secret: str, algorithm: str, expire_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expire_minutes)).timestamp()),
    }
    return pyjwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str, secret: str, algorithm: str) -> str | None:
    """Return user_id from a valid token, else None."""
    try:
        payload = pyjwt.decode(token, secret, algorithms=[algorithm])
        return payload.get("sub")
    except pyjwt.PyJWTError:
        return None
