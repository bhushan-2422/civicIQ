"""
Main Service — Firestore Document Helpers
Replaces SQLAlchemy models. All data stored as Firestore documents.
Collections: 'complaints', 'users', 'complaint_reporters'
"""
import uuid
from datetime import datetime, timezone

# ─── Constants ────────────────────────────────────────────────────────────────

CATEGORY_VALUES = (
    "ROAD_DAMAGE", "WATER_LEAKAGE", "STREETLIGHT",
    "TRAFFIC_SIGNAL", "SEWERAGE", "GARBAGE", "TREE_FALL", "OTHER",
)

DEPARTMENT_VALUES = (
    "ROADS", "WATER", "ELECTRICITY", "TRAFFIC",
    "SANITATION", "SEWER", "PARKS", "OTHER",
)

STATUS_VALUES = (
    "PROCESSING", "VALID", "IN_PROGRESS", "RESOLVED", "REJECTED",
)

# Firestore collection names
COLLECTION_COMPLAINTS = "complaints"
COLLECTION_USERS = "users"
COLLECTION_REPORTERS = "complaint_reporters"


# ─── Utilities ────────────────────────────────────────────────────────────────

def new_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ts_to_iso(val) -> str | None:
    """Convert Firestore Timestamp or datetime to ISO string."""
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


# ─── Complaint document builder ───────────────────────────────────────────────

def build_complaint_doc(
    description: str,
    latitude: float,
    longitude: float,
    reporter_name: str,
    reporter_phone: str,
    reporter_credibility: float = 0.5,
    image_url: str | None = None,
) -> dict:
    """Build a new complaint Firestore document."""
    now = utc_now()
    return {
        "id": new_uuid(),
        "category": None,
        "department": None,
        "description": description,
        "imageUrl": image_url,
        "latitude": latitude,
        "longitude": longitude,
        "priorityScore": 0.0,
        "severityScore": 0.0,
        "communityValidation": 0.0,
        "reporterCredibility": reporter_credibility,
        "estimatedCost": 0,
        "estimatedDuration": None,
        "summary": None,
        "status": "PROCESSING",
        "reporterName": reporter_name,
        "reporterPhone": reporter_phone,
        "isDuplicate": False,
        "parentComplaintId": None,
        "reporterCount": 1,
        "createdAt": now,
        "updatedAt": now,
    }


def build_user_doc(name: str, phone: str) -> dict:
    """Build a new user Firestore document."""
    now = utc_now()
    return {
        "id": phone,          # Use phone as document ID for fast lookup
        "name": name,
        "phone": phone,
        "credibilityScore": 0.5,
        "validatedCount": 0,
        "rejectedCount": 0,
        "createdAt": now,
        "updatedAt": now,
    }


def complaint_to_dict(doc: dict) -> dict:
    """Serialize a Firestore complaint document to a JSON-safe dict."""
    return {
        "id": doc.get("id"),
        "category": doc.get("category"),
        "department": doc.get("department"),
        "description": doc.get("description"),
        "imageUrl": doc.get("imageUrl"),
        "latitude": doc.get("latitude"),
        "longitude": doc.get("longitude"),
        "priorityScore": float(doc.get("priorityScore") or 0.0),
        "severityScore": float(doc.get("severityScore") or 0.0),
        "communityValidation": float(doc.get("communityValidation") or 0.0),
        "reporterCredibility": float(doc.get("reporterCredibility") or 0.5),
        "estimatedCost": doc.get("estimatedCost") or 0,
        "estimatedDuration": doc.get("estimatedDuration"),
        "summary": doc.get("summary"),
        "status": doc.get("status", "PROCESSING"),
        "reporterName": doc.get("reporterName"),
        "reporterPhone": doc.get("reporterPhone"),
        "isDuplicate": bool(doc.get("isDuplicate", False)),
        "parentComplaintId": doc.get("parentComplaintId"),
        "reporterCount": doc.get("reporterCount", 1),
        "createdAt": ts_to_iso(doc.get("createdAt")),
        "updatedAt": ts_to_iso(doc.get("updatedAt")),
    }


def user_to_dict(doc: dict) -> dict:
    """Serialize a Firestore user document to a JSON-safe dict."""
    return {
        "id": doc.get("id"),
        "name": doc.get("name"),
        "phone": doc.get("phone"),
        "credibilityScore": float(doc.get("credibilityScore") or 0.5),
        "validatedCount": doc.get("validatedCount") or 0,
        "rejectedCount": doc.get("rejectedCount") or 0,
        "createdAt": ts_to_iso(doc.get("createdAt")),
    }
