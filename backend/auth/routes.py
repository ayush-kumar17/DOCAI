"""
Auth routes.

POST /api/auth/register  — create account
POST /api/auth/login     — get JWT token
GET  /api/auth/me        — get current user info
"""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from auth.service import create_user, authenticate_user, create_access_token
from auth.dependencies import get_current_user
from auth.schemas import RegisterRequest, TokenResponse, UserResponse
from database.models import User

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db:   AsyncSession = Depends(get_db),
):
    """
    Create a new account.
    Returns a JWT token immediately so user is logged in after registering.
    """
    user  = await create_user(
        email    = body.email,
        username = body.username,
        password = body.password,
        db       = db,
    )

    token = create_access_token(str(user.id))

    return TokenResponse(
        access_token = token,
        user_id      = str(user.id),
        username     = user.username,
        email        = user.email,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db:   AsyncSession = Depends(get_db),
):
    """
    Login with email + password.
    Uses OAuth2PasswordRequestForm so it works with
    Swagger UI's Authorize button out of the box.
    Note: form.username field is used for email.
    """
    user  = await authenticate_user(
        email    = form.username,   # OAuth2 form uses 'username' field
        password = form.password,
        db       = db,
    )

    token = create_access_token(str(user.id))

    return TokenResponse(
        access_token = token,
        user_id      = str(user.id),
        username     = user.username,
        email        = user.email,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Return the currently logged-in user's info.
    Requires Authorization: Bearer <token> header.
    """
    return UserResponse(
        id         = str(current_user.id),
        email      = current_user.email,
        username   = current_user.username,
        created_at = current_user.created_at,
    )