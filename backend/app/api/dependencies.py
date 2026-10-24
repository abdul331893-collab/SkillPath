from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from app.core.security import verify_token
from app.core.permissions import AuthenticatedUser, UserRole
from app.repositories.firestore_repo import FirestoreRepository

async def get_current_user(authorization: Optional[str] = Header(None)) -> AuthenticatedUser:
    """
    Extracts Bearer token from header and validates user identity.
    Checks authoritative database record for user role.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split("Bearer ")[1].strip()
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    uid = payload.get("uid") or payload.get("user_id")
    email = payload.get("email", "")
    name = payload.get("name") or payload.get("display_name")
    email_verified = payload.get("email_verified", False)

    from app.core.config import settings

    # Check database for assigned role
    db_user = FirestoreRepository.get_document("users", uid)
    role = UserRole.STUDENT

    # Known admin emails check
    admin_emails = [e.strip().lower() for e in (getattr(settings, "ADMIN_EMAILS", "admin@skillpath.ai") or "admin@skillpath.ai").split(",") if e.strip()]
    is_admin_email = bool(email and email.strip().lower() in admin_emails) or (email and email.strip().lower() == "admin@skillpath.ai")

    if is_admin_email:
        role = UserRole.ADMIN
        if db_user and db_user.get("role") != "admin":
            FirestoreRepository.update_document("users", uid, {"role": "admin"})
    elif db_user and db_user.get("role"):
        try:
            role = UserRole(db_user.get("role"))
        except ValueError:
            role = UserRole.STUDENT
    elif payload.get("role") == "admin":
        role = UserRole.ADMIN

    return AuthenticatedUser(
        uid=uid,
        email=email,
        name=name,
        role=role,
        email_verified=email_verified,
    )

async def require_student(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Ensures caller has at least student or admin privileges."""
    return user

async def require_admin(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Ensures caller has admin privileges."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required for this action",
        )
    return user
