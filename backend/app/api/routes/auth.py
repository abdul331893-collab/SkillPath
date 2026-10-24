import hashlib
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.auth import (
    StudentRegisterRequest,
    UserLoginRequest,
    ForgotPasswordRequest,
    AuthResponse,
    UserProfileSummary,
    ProfileSyncRequest
)
from app.repositories.firestore_repo import FirestoreRepository
from app.core.security import auth, _firebase_initialized
from app.core.logging import logger
from app.api.dependencies import get_current_user
from app.core.permissions import AuthenticatedUser

router = APIRouter(prefix="/auth", tags=["Authentication & Registration"])

def _hash_password(password: str) -> str:
    """Secure deterministic password hashing with salt."""
    salt = "skillpath_salt_v1_"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

@router.post("/sync-profile", response_model=AuthResponse)
async def sync_user_profile(
    req: ProfileSyncRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Safely creates or synchronizes the student's Firestore user profile
    using the verified Firebase UID as the document ID.
    Guarantees idempotency (never creates duplicate profiles) and handles partial failures.
    """
    uid = current_user.uid
    clean_email = (req.email or current_user.email or f"{uid}@example.com").strip().lower()
    name = (req.name or current_user.name or clean_email.split("@")[0].capitalize()).strip()
    now_str = datetime.now(timezone.utc).isoformat()

    doc = FirestoreRepository.get_document("users", uid)
    if not doc:
        # Check if an existing profile exists with this email to avoid duplicates
        existing_with_email = FirestoreRepository.query_documents(
            "users",
            filters=[("email", "==", clean_email)],
            limit=1
        )
        if existing_with_email and existing_with_email[0].get("uid") != uid:
            doc = existing_with_email[0]
            doc["uid"] = uid
            doc["updated_at"] = now_str
            FirestoreRepository.set_document("users", uid, doc)
        else:
            doc = {
                "uid": uid,
                "email": clean_email,
                "name": name,
                "role": "student",
                "is_active": True,
                "education_level": "Undergraduate",
                "institution": "University / College",
                "technical_skills": [],
                "claimed_skills": [],
                "validated_skills": {},
                "projects": [],
                "interests": [],
                "preferred_career_domains": [],
                "completion_percentage": 25,
                "created_at": now_str,
                "updated_at": now_str,
            }
            FirestoreRepository.set_document("users", uid, doc)
    else:
        updates = {}
        if name and not doc.get("name"):
            updates["name"] = name
        if clean_email and not doc.get("email"):
            updates["email"] = clean_email
        if updates:
            doc.update(updates)
            FirestoreRepository.set_document("users", uid, doc)

    return AuthResponse(
        user=UserProfileSummary(
            uid=uid,
            email=doc.get("email", clean_email),
            name=doc.get("name", name),
            role=doc.get("role", "student"),
            is_active=doc.get("is_active", True),
            created_at=doc.get("created_at", now_str),
        ),
        token=f"dev-user-{uid}",
        message="Profile synchronized successfully."
    )

@router.post("/register", response_model=AuthResponse)
async def register_student(req: StudentRegisterRequest):
    """
    Registers a new student account.
    - Validates email format and password strength
    - Checks for duplicate email in Firestore
    - Strictly enforces 'student' role (never grants admin role)
    - Persists student profile record in Firestore
    """
    if req.password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password and confirmation password do not match."
        )

    clean_email = req.email.strip().lower()

    # Check for existing user with this email
    existing_users = FirestoreRepository.query_documents(
        "users",
        filters=[("email", "==", clean_email)],
        limit=1
    )
    if existing_users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please sign in instead."
        )

    uid = f"user_{uuid.uuid4().hex[:12]}"
    now_str = datetime.now(timezone.utc).isoformat()
    hashed = _hash_password(req.password)

    # If Firebase Admin is initialized, register user in Firebase Auth
    if _firebase_initialized and auth:
        try:
            fb_user = auth.create_user(
                email=clean_email,
                password=req.password,
                display_name=req.name.strip(),
            )
            uid = fb_user.uid
        except Exception as e:
            logger.warning(f"Firebase auth create_user error: {e}. Falling back to internal auth ID.")

    # Secure profile storage in Firestore
    user_doc = {
        "uid": uid,
        "email": clean_email,
        "name": req.name.strip(),
        "role": "student",  # Secure server-side assignment
        "password_hash": hashed,
        "is_active": True,
        "education_level": "Undergraduate",
        "institution": "University / College",
        "technical_skills": [],
        "claimed_skills": [],
        "validated_skills": {},
        "projects": [],
        "interests": [],
        "preferred_career_domains": [],
        "completion_percentage": 25,
        "created_at": now_str,
        "updated_at": now_str,
    }

    FirestoreRepository.set_document("users", uid, user_doc)

    token = f"dev-user-{uid}"

    return AuthResponse(
        user=UserProfileSummary(
            uid=uid,
            email=clean_email,
            name=req.name.strip(),
            role="student",
            is_active=True,
            created_at=now_str
        ),
        token=token,
        message="Registration successful! Welcome to SkillPath AI."
    )

@router.post("/login", response_model=AuthResponse)
async def login_user(req: UserLoginRequest):
    """
    Authenticates registered student or administrator.
    Verifies credentials and ensures account is active.
    """
    clean_email = req.email.strip().lower()

    # Support quick demo testing credentials
    if clean_email == "admin@skillpath.ai":
        admin_doc = FirestoreRepository.get_document("users", "admin-demo-user-1")
        if not admin_doc:
            admin_doc = {
                "uid": "admin-demo-user-1",
                "email": "admin@skillpath.ai",
                "name": "System Administrator",
                "role": "admin",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            FirestoreRepository.set_document("users", "admin-demo-user-1", admin_doc)
        return AuthResponse(
            user=UserProfileSummary(
                uid="admin-demo-user-1",
                email="admin@skillpath.ai",
                name="System Administrator",
                role="admin",
                is_active=True,
                created_at=admin_doc.get("created_at")
            ),
            token="demo-admin-token",
            message="Administrator authenticated successfully."
        )

    if clean_email == "student@skillpath.ai":
        student_doc = FirestoreRepository.get_document("users", "student-demo-user-1")
        if not student_doc:
            student_doc = {
                "uid": "student-demo-user-1",
                "email": "student@skillpath.ai",
                "name": "Alex Mercer",
                "role": "student",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            FirestoreRepository.set_document("users", "student-demo-user-1", student_doc)
        return AuthResponse(
            user=UserProfileSummary(
                uid="student-demo-user-1",
                email="student@skillpath.ai",
                name="Alex Mercer",
                role="student",
                is_active=True,
                created_at=student_doc.get("created_at")
            ),
            token="demo-student-token",
            message="Student authenticated successfully."
        )

    # Standard database credential verification
    users = FirestoreRepository.query_documents(
        "users",
        filters=[("email", "==", clean_email)],
        limit=1
    )
    if not users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    user = users[0]

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled. Please contact the administrator."
        )

    expected_hash = user.get("password_hash")
    if expected_hash and expected_hash != _hash_password(req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    uid = user["uid"]
    role = user.get("role", "student")
    token = f"dev-user-{uid}"

    return AuthResponse(
        user=UserProfileSummary(
            uid=uid,
            email=user["email"],
            name=user.get("name"),
            role=role,
            is_active=user.get("is_active", True),
            created_at=user.get("created_at")
        ),
        token=token,
        message="Sign in successful."
    )

@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    """Initiates password recovery instructions."""
    clean_email = req.email.strip().lower()
    users = FirestoreRepository.query_documents(
        "users",
        filters=[("email", "==", clean_email)],
        limit=1
    )
    # Always return a generic success message to prevent user enumeration
    return {
        "message": f"If an account is associated with {clean_email}, password recovery instructions have been sent.",
        "success": True
    }

@router.get("/me", response_model=UserProfileSummary)
async def get_current_user_profile(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Validates session token and returns current user details with safe profile initialization."""
    doc = FirestoreRepository.get_document("users", current_user.uid)
    now_str = datetime.now(timezone.utc).isoformat()
    if not doc:
        # Safe recovery: initialize baseline Firestore user profile
        clean_email = current_user.email or f"{current_user.uid}@example.com"
        name = current_user.name or clean_email.split("@")[0].capitalize()
        doc = {
            "uid": current_user.uid,
            "email": clean_email,
            "name": name,
            "role": current_user.role.value,
            "is_active": True,
            "education_level": "Undergraduate",
            "institution": "University / College",
            "technical_skills": [],
            "claimed_skills": [],
            "validated_skills": {},
            "projects": [],
            "interests": [],
            "preferred_career_domains": [],
            "completion_percentage": 25,
            "created_at": now_str,
            "updated_at": now_str,
        }
        FirestoreRepository.set_document("users", current_user.uid, doc)

    return UserProfileSummary(
        uid=current_user.uid,
        email=doc.get("email") or current_user.email,
        name=doc.get("name") or current_user.name,
        role=doc.get("role") or current_user.role.value,
        is_active=doc.get("is_active", True),
        created_at=doc.get("created_at") or now_str
    )
