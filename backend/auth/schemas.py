"""
Pydantic schemas for auth routes.
These define what the API accepts and returns.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


# ──────────────────────────────────────────────
# Request schemas (what client sends)
# ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email:    EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 50:
            raise ValueError("Username must be under 50 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


# ──────────────────────────────────────────────
# Response schemas (what API returns)
# ──────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user_id:      str
    username:     str
    email:        str


class UserResponse(BaseModel):
    id:         str
    email:      str
    username:   str
    created_at: datetime

    class Config:
        from_attributes = True