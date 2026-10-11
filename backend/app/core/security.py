import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()

# --- Password hashing ---
# bcrypt: industry-standard, deliberately slow (resists brute-force), and
# automatically generates/stores a unique salt per password inside the hash
# itself. Passwords are HASHED (one-way) - nobody, including us, can ever
# recover the original password from what's stored in the database.
BCRYPT_MAX_BYTES = 72  # bcrypt silently ignores bytes beyond this length


def hash_password(plain_password: str) -> str:
    truncated = plain_password.encode("utf-8")[:BCRYPT_MAX_BYTES]
    hashed = bcrypt.hashpw(truncated, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    truncated = plain_password.encode("utf-8")[:BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(truncated, password_hash.encode("utf-8"))
    except (ValueError, AttributeError):
        # Malformed/empty hash (e.g. a leftover plaintext value from before
        # this fix) - treat as "wrong password" rather than crashing.
        return False


# --- JWT access tokens ---
# JWT_SECRET_KEY must be set in .env for any real deployment - the fallback
# here only exists so local dev doesn't crash if it's missing. Never rely
# on the fallback outside your own machine.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-insecure-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days - simple long-lived token for a quiz app


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[int]:
    """Returns the user_id encoded in the token, or None if invalid/expired/tampered."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        return int(user_id) if user_id is not None else None
    except jwt.PyJWTError:
        return None
