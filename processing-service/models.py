"""
Processing Service — Firestore Document Helpers
Mirrors main-service/models.py. Shared constants and serialisation helpers.
"""
from datetime import datetime, timezone

# ─── Collection names ─────────────────────────────────────────────────────────
COLLECTION_COMPLAINTS = "complaints"
COLLECTION_USERS = "users"
COLLECTION_REPORTERS = "complaint_reporters"

# ─── Enum constants ───────────────────────────────────────────────────────────
CATEGORY_VALUES = (
    "ROAD_DAMAGE", "WATER_LEAKAGE", "STREETLIGHT",
    "TRAFFIC_SIGNAL", "SEWERAGE", "GARBAGE", "TREE_FALL", "OTHER",
)

DEPARTMENT_VALUES = (
    "ROADS", "WATER", "ELECTRICITY", "TRAFFIC",
    "SANITATION", "SEWER", "PARKS", "OTHER",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ts_to_iso(val) -> str | None:
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


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
