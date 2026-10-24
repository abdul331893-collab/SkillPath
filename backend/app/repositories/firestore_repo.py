import json
import os
import uuid
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path
from app.core.config import settings
from app.core.logging import logger
import app.core.security as security

# In-memory and local disk persistence file
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_PERSISTENCE_FILE = _BACKEND_DIR / "uploads" / "local_firestore.json"

_memory_store: Dict[str, Dict[str, Any]] = {
    "users": {},
    "resumes": {},
    "questions": {},
    "assessments": {},
    "career_domains": {},
    "career_recommendations": {},
    "roadmaps": {},
    "jobs": {},
    "applications": {},
    "learning_resources": {},
}

_seeded = False

def _save_store_to_disk():
    """Atomically persists the store to disk for reliable local dev persistence."""
    try:
        os.makedirs(_PERSISTENCE_FILE.parent, exist_ok=True)
        temp_file = _PERSISTENCE_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(_memory_store, f, indent=2, ensure_ascii=False)
        try:
            os.replace(temp_file, _PERSISTENCE_FILE)
        except Exception:
            import shutil
            shutil.copyfile(temp_file, _PERSISTENCE_FILE)
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Could not persist local store to disk: {e}")

def _load_store_from_disk():
    """Loads previously saved documents from disk on startup."""
    global _memory_store
    if _PERSISTENCE_FILE.exists():
        try:
            with open(_PERSISTENCE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                for coll, docs in loaded.items():
                    if coll not in _memory_store:
                        _memory_store[coll] = {}
                    _memory_store[coll].update(docs)
            logger.info(f"Loaded persistent local datastore from {_PERSISTENCE_FILE}")
        except Exception as e:
            logger.warning(f"Could not read local persistence file: {e}")

# Load immediately on module load
_load_store_from_disk()

def _ensure_default_seed():
    """Seeds default demo accounts if missing."""
    global _seeded
    if _seeded:
        return
    _seeded = True

    now_str = datetime.now(timezone.utc).isoformat()

    # Default Demo Users
    if "admin-demo-user-1" not in _memory_store["users"]:
        _memory_store["users"]["admin-demo-user-1"] = {
            "id": "admin-demo-user-1",
            "uid": "admin-demo-user-1",
            "email": "admin@skillpath.ai",
            "name": "System Administrator",
            "role": "admin",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": now_str,
        }
    if "student-demo-user-1" not in _memory_store["users"]:
        _memory_store["users"]["student-demo-user-1"] = {
            "id": "student-demo-user-1",
            "uid": "student-demo-user-1",
            "email": "student@skillpath.ai",
            "name": "Alex Mercer",
            "role": "student",
            "is_active": True,
            "education_level": "Undergraduate",
            "institution": "Stanford University",
            "claimed_skills": ["React", "JavaScript", "Python", "FastAPI", "SQL & Databases"],
            "technical_skills": ["React", "JavaScript", "Python"],
            "validated_skills": {"React": 85.0, "JavaScript": 80.0, "Python": 75.0},
            "projects": [
                {
                    "title": "E-Commerce Platform",
                    "description": "Full-stack shopping application built with React and FastAPI.",
                    "technologies": ["React", "JavaScript", "FastAPI", "SQL & Databases"]
                }
            ],
            "completion_percentage": 75,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": now_str,
        }
    _save_store_to_disk()

# Run seed check
_ensure_default_seed()

def _get_firestore_client():
    """Returns Cloud Firestore client if initialized with valid credentials; else None."""
    security.init_firebase()
    if security._firebase_initialized and security._has_credentials and security.firestore:
        try:
            return security.firestore.client()
        except Exception as e:
            logger.warning(f"Could not obtain Firestore client from Admin SDK: {e}")
            return None
    return None

class FirestoreRepository:
    """Repository handling all CRUD interactions with Firestore or persistent disk storage."""

    @staticmethod
    def get_document(collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        t0 = time.time()
        client = _get_firestore_client()
        if client:
            try:
                doc = client.collection(collection).document(doc_id).get()
                duration = round((time.time() - t0) * 1000, 2)
                logger.debug(f"[Firestore:Read] {collection}/{doc_id} in {duration}ms")
                if doc.exists:
                    data = doc.to_dict()
                    data["id"] = doc.id
                    return data
                return None
            except Exception as e:
                logger.warning(f"Firestore get_document error on {collection}/{doc_id}: {e}. Falling back to persistent storage.")

        # Local persistent store fallback
        _ensure_default_seed()
        coll = _memory_store.get(collection, {})
        res = coll.get(doc_id)
        if res:
            return dict(res)
        return None

    @staticmethod
    def set_document(collection: str, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        t0 = time.time()
        if "id" not in data:
            data["id"] = doc_id
        if "updated_at" not in data:
            data["updated_at"] = datetime.now(timezone.utc).isoformat()

        client = _get_firestore_client()
        if client:
            try:
                client.collection(collection).document(doc_id).set(data)
                duration = round((time.time() - t0) * 1000, 2)
                logger.debug(f"[Firestore:Set] {collection}/{doc_id} in {duration}ms")
            except Exception as e:
                logger.warning(f"Firestore set_document error on {collection}/{doc_id}: {e}. Writing to persistent storage.")

        # Always update local cache & disk store for instant consistency
        if collection not in _memory_store:
            _memory_store[collection] = {}
        _memory_store[collection][doc_id] = dict(data)
        _save_store_to_disk()
        return data

    @staticmethod
    def update_document(collection: str, doc_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        t0 = time.time()
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        client = _get_firestore_client()
        if client:
            try:
                doc_ref = client.collection(collection).document(doc_id)
                doc_ref.update(updates)
                doc = doc_ref.get()
                duration = round((time.time() - t0) * 1000, 2)
                logger.debug(f"[Firestore:Update] {collection}/{doc_id} in {duration}ms")
                if doc.exists:
                    d = doc.to_dict()
                    d["id"] = doc.id
                    if collection in _memory_store:
                        _memory_store[collection][doc_id] = dict(d)
                        _save_store_to_disk()
                    return d
            except Exception as e:
                logger.warning(f"Firestore update_document error on {collection}/{doc_id}: {e}. Updating local persistent storage.")

        # Local persistent store fallback
        _ensure_default_seed()
        coll = _memory_store.get(collection, {})
        if doc_id in coll:
            coll[doc_id].update(updates)
            _save_store_to_disk()
            return dict(coll[doc_id])
        return None

    @staticmethod
    def delete_document(collection: str, doc_id: str) -> bool:
        t0 = time.time()
        client = _get_firestore_client()
        if client:
            try:
                client.collection(collection).document(doc_id).delete()
                duration = round((time.time() - t0) * 1000, 2)
                logger.debug(f"[Firestore:Delete] {collection}/{doc_id} in {duration}ms")
            except Exception as e:
                logger.warning(f"Firestore delete_document error on {collection}/{doc_id}: {e}")

        # Local persistent store fallback
        _ensure_default_seed()
        coll = _memory_store.get(collection, {})
        if doc_id in coll:
            del coll[doc_id]
            _save_store_to_disk()
            return True
        return False

    @staticmethod
    def query_documents(collection: str, filters: Optional[List[tuple]] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Query documents. filters format: [(field, op, val)]
        e.g. [("user_id", "==", "uid123")]
        """
        t0 = time.time()
        client = _get_firestore_client()
        if client:
            try:
                ref = client.collection(collection)
                if filters:
                    for field, op, val in filters:
                        ref = ref.where(field, op, val)
                docs = ref.limit(limit).stream()
                results = []
                for doc in docs:
                    d = doc.to_dict()
                    d["id"] = doc.id
                    results.append(d)
                duration = round((time.time() - t0) * 1000, 2)
                logger.debug(f"[Firestore:Query] {collection} returned {len(results)} docs in {duration}ms")
                return results
            except Exception as e:
                logger.warning(f"Firestore query_documents error on {collection}: {e}. Querying persistent local storage.")

        # Local persistent store fallback
        _ensure_default_seed()
        coll = _memory_store.get(collection, {})
        results = []
        for doc in coll.values():
            match = True
            if filters:
                for field, op, val in filters:
                    doc_val = doc.get(field)
                    if op == "==" and doc_val != val:
                        match = False
                        break
                    elif op == "!=" and doc_val == val:
                        match = False
                        break
                    elif op == "in" and (val is None or doc_val not in val):
                        match = False
                        break
                    elif op == ">=" and (doc_val is None or doc_val < val):
                        match = False
                        break
                    elif op == "<=" and (doc_val is None or doc_val > val):
                        match = False
                        break
            if match:
                results.append(dict(doc))
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def count_documents(collection: str) -> int:
        client = _get_firestore_client()
        if client:
            try:
                count_query = client.collection(collection).count()
                return count_query.get()[0][0].value
            except Exception:
                pass
        _ensure_default_seed()
        return len(_memory_store.get(collection, {}))
