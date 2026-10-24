import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, field_validator

EMAIL_REGEX = r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)+$"

class StudentRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip()
        if not re.match(EMAIL_REGEX, v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v

class UserLoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip()
        if not re.match(EMAIL_REGEX, v):
            raise ValueError("Invalid email format")
        return v

class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip()
        if not re.match(EMAIL_REGEX, v):
            raise ValueError("Invalid email format")
        return v

class UserProfileSummary(BaseModel):
    uid: str
    email: str
    name: Optional[str] = None
    role: str
    is_active: bool = True
    created_at: Optional[str] = None

class AuthResponse(BaseModel):
    user: UserProfileSummary
    token: str
    message: str

class ProfileSyncRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
