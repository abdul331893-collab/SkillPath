from enum import Enum
from typing import Optional
from pydantic import BaseModel

class UserRole(str, Enum):
    STUDENT = "student"
    ADMIN = "admin"

class AuthenticatedUser(BaseModel):
    uid: str
    email: str
    name: Optional[str] = None
    role: UserRole = UserRole.STUDENT
    email_verified: bool = False
