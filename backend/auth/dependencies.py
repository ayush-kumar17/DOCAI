"""
FastAPI dependencies for authentication.

get_current_user is injected into any route that requires login:

    @router.get("/protected")
    async def protected(user: User = Depends(get_current_user)):
        return {"user": user.email}
"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import User
from auth.service import decode_token, get_user_by_id
from utils.exceptions import Unauthorized

# This tells FastAPI where to look for the token
# and auto-generates the Authorize button in Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db:    AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency that:
    1. Extracts the Bearer token from the Authorization header
    2. Decodes + verifies it
    3. Loads and returns the User from the database
    4. Raises 401 if anything fails
    """
    # Decode JWT → get user_id
    user_id = decode_token(token)

    # Load user from DB
    user = await get_user_by_id(user_id, db)
    if not user or not user.is_active:
        raise Unauthorized()

    return user