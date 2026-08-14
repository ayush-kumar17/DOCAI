"""
Auth service — password hashing, token creation, user lookup.
Business logic lives here. Routes are thin wrappers that call this.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User
from config import settings
from utils.logger import get_logger
from utils.exceptions import Unauthorized, EmailAlreadyExists

logger = get_logger(__name__)

# bcrypt password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ──────────────────────────────────────────────
# Password helpers
# ──────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash a plain text password using bcrypt."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Check plain text password against bcrypt hash."""
    return pwd_context.verify(plain, hashed)


# ──────────────────────────────────────────────
# JWT helpers
# ──────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    """
    Create a signed JWT token.
    Payload contains:
      sub  — user id (standard JWT claim)
      exp  — expiry timestamp
      iat  — issued at
    """
    now    = datetime.utcnow()
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "iat": now,
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm="HS256",
    )

    return token


def decode_token(token: str) -> str:
    """
    Decode and verify a JWT token.
    Returns the user_id (sub claim).
    Raises Unauthorized on any failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise Unauthorized()
        return user_id

    except JWTError:
        raise Unauthorized()


# ──────────────────────────────────────────────
# User operations
# ──────────────────────────────────────────────

async def get_user_by_email(email: str, db: AsyncSession) -> Optional[User]:
    """Fetch a user by email address."""
    result = await db.execute(
        select(User).where(User.email == email.lower().strip())
    )
    return result.scalar_one_or_none()


async def get_user_by_id(user_id: str, db: AsyncSession) -> Optional[User]:
    """Fetch a user by UUID."""
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    return result.scalar_one_or_none()


async def create_user(
    email:    str,
    username: str,
    password: str,
    db:       AsyncSession,
) -> User:
    """
    Create a new user.
    Raises EmailAlreadyExists if email is taken.
    """
    # Check email uniqueness
    existing = await get_user_by_email(email, db)
    if existing:
        raise EmailAlreadyExists()

    user = User(
        email     = email.lower().strip(),
        username  = username.strip(),
        hashed_pw = hash_password(password),
    )

    db.add(user)
    await db.flush()   # get the id without committing

    logger.info("User created", user_id=str(user.id), email=user.email)
    return user


async def authenticate_user(
    email:    str,
    password: str,
    db:       AsyncSession,
) -> User:
    """
    Verify email + password.
    Returns the User if valid.
    Raises Unauthorized if invalid.
    """
    user = await get_user_by_email(email, db)

    # Use same error for wrong email OR wrong password
    # (don't reveal which one was wrong — security best practice)
    if not user or not verify_password(password, user.hashed_pw):
        raise Unauthorized()

    if not user.is_active:
        raise Unauthorized()

    logger.info("User authenticated", user_id=str(user.id))
    return user