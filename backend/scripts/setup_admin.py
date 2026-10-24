"""
Secure Administrator Account Setup and Verification Tool for SkillPath AI.

Usage:
    python scripts/setup_admin.py [--email admin@gmail.com]

This tool:
1. Connects securely to the intended Firebase project (skillpath-c8115).
2. Verifies whether the administrator account exists in Firebase Authentication.
3. Sets up or updates the account in Firebase Authentication if needed.
4. Assigns the server-side administrator role in Firebase claims and Firestore.
5. NEVER logs, prints, or exposes administrative credentials.
"""

import os
import sys
import json
import getpass
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to sys.path so app modules can be loaded
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.security import init_firebase, _has_credentials, _firebase_initialized, auth as fa_auth
from app.repositories.firestore_repo import FirestoreRepository

API_KEY = os.environ.get("NEXT_PUBLIC_FIREBASE_API_KEY", "AIzaSyDjhTnHLQ1NGr8r2KR7zTwcdnKdpF5oasY")

def setup_admin_account(email: str, password: str = None) -> bool:
    clean_email = email.strip().lower()
    print(f"\n[SkillPath AI] Initiating administrator verification for: {clean_email}")
    print(f"[SkillPath AI] Target Firebase Project: {settings.FIREBASE_PROJECT_ID or 'skillpath-c8115'}")

    # Prompt securely if password was not passed via environment variable
    if not password:
        password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Enter administrator password: ")

    if not password or len(password) < 6:
        print("[Error] Password must be at least 6 characters long.")
        return False

    now_str = datetime.now(timezone.utc).isoformat()
    uid = None

    # Method 1: Use Firebase Admin SDK if service account credentials are loaded
    init_firebase()
    if _firebase_initialized and _has_credentials and fa_auth:
        print("[Admin SDK] Using authoritative Firebase Admin SDK...")
        try:
            user_record = fa_auth.get_user_by_email(clean_email)
            uid = user_record.uid
            print(f"[Admin SDK] Found existing Firebase Auth user with UID: {uid}")
            fa_auth.update_user(uid, password=password)
            print("[Admin SDK] Password successfully synchronized for existing account.")
        except Exception:
            try:
                user_record = fa_auth.create_user(
                    email=clean_email,
                    password=password,
                    display_name="System Administrator"
                )
                uid = user_record.uid
                print(f"[Admin SDK] Successfully created administrator user in Firebase Auth with UID: {uid}")
            except Exception as create_err:
                print(f"[Admin SDK] Failed to create user via Admin SDK: {create_err}")
                uid = None

        if uid:
            try:
                fa_auth.set_custom_user_claims(uid, {"role": "admin"})
                print("[Admin SDK] Custom claims set: {'role': 'admin'}")
            except Exception as claim_err:
                print(f"[Admin SDK] Note setting custom claims: {claim_err}")

    # Method 2: Firebase Identity Toolkit REST API
    if not uid:
        print("[REST API] Connecting via Firebase Authentication Identity Toolkit...")
        # Check if already signable
        sign_in_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
        payload = json.dumps({"email": clean_email, "password": password, "returnSecureToken": True}).encode("utf-8")
        req = urllib.request.Request(sign_in_url, data=payload, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                uid = res_data.get("localId")
                print(f"[REST API] Credentials verified successfully! Firebase UID: {uid}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_body)
                err_msg = err_json.get("error", {}).get("message", "")
            except Exception:
                err_msg = err_body

            if "INVALID_LOGIN_CREDENTIALS" in err_msg or "EMAIL_NOT_FOUND" in err_msg:
                # User might not exist yet; attempt sign up
                print("[REST API] Account not found or password mismatched. Attempting user registration...")
                signup_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
                signup_payload = json.dumps({"email": clean_email, "password": password, "returnSecureToken": True}).encode("utf-8")
                signup_req = urllib.request.Request(signup_url, data=signup_payload, headers={"Content-Type": "application/json"})

                try:
                    with urllib.request.urlopen(signup_req) as s_resp:
                        s_data = json.loads(s_resp.read().decode("utf-8"))
                        uid = s_data.get("localId")
                        print(f"[REST API] Successfully registered administrator account in Firebase Auth! UID: {uid}")
                except urllib.error.HTTPError as s_err:
                    s_body = s_err.read().decode("utf-8")
                    if "EMAIL_EXISTS" in s_body:
                        print(f"[REST API] Account '{clean_email}' already exists in Firebase Auth, but the supplied password did not match.")
                        print("[REST API] Triggering password-reset flow...")
                        reset_url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={API_KEY}"
                        reset_payload = json.dumps({"requestType": "PASSWORD_RESET", "email": clean_email}).encode("utf-8")
                        r_req = urllib.request.Request(reset_url, data=reset_payload, headers={"Content-Type": "application/json"})
                        try:
                            with urllib.request.urlopen(r_req) as r_resp:
                                print(f"[REST API] Password reset email has been dispatched to '{clean_email}'. Please check your inbox.")
                        except Exception as r_err:
                            print(f"[REST API] Error dispatching reset email: {r_err}")
                        return False
                    else:
                        print(f"[REST API] Registration error: {s_body}")
                        return False
            else:
                print(f"[REST API] Authentication API returned: {err_msg}")
                return False

    if not uid:
        print("[Error] Could not verify or establish administrator UID in Firebase Authentication.")
        return False

    # Synchronize Firestore authoritative administrator record
    print(f"[Firestore] Ensuring authoritative administrator profile in Firestore: users/{uid}")
    admin_doc = FirestoreRepository.get_document("users", uid) or {}
    admin_doc.update({
        "uid": uid,
        "email": clean_email,
        "name": "System Administrator",
        "role": "admin",
        "is_active": True,
        "updated_at": now_str,
    })
    if "created_at" not in admin_doc:
        admin_doc["created_at"] = now_str

    FirestoreRepository.set_document("users", uid, admin_doc)
    print(f"[Firestore] Record successfully written for {clean_email} with role='admin'.")
    print("\n[SUCCESS] Administrator account is fully configured and ready for login.")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SkillPath AI Administrator Account Setup")
    parser.add_argument("--email", default="admin@gmail.com", help="Administrator email address")
    args = parser.parse_args()
    success = setup_admin_account(args.email)
    sys.exit(0 if success else 1)
