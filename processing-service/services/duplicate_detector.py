"""
Processing Service — Duplicate Detector (Firestore)
Detects duplicate complaints using geo-distance and time-window Firestore queries.
No SQL, no ORM — pure Firestore and Haversine math.
"""
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger("processing-service.duplicate_detector")


# ─── Haversine Formula ────────────────────────────────────────────────────────

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance in metres between two GPS coordinates.

    Args:
        lat1, lon1: First point (decimal degrees).
        lat2, lon2: Second point (decimal degrees).

    Returns:
        Distance in metres.
    """
    R = 6_371_000  # Earth radius in metres

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# Re-export under the legacy internal name used by priority_calculator.py
_haversine = haversine_distance


# ─── Duplicate Detection ──────────────────────────────────────────────────────

def find_duplicate(
    db,
    category: str,
    latitude: float,
    longitude: float,
    radius_meters: float,
    days: int,
    exclude_complaint_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Find an existing complaint that matches the duplicate criteria.

    Duplicate criteria:
        1. Same category
        2. Within radius_meters distance (Haversine)
        3. Created within the last `days` days
        4. Not itself a duplicate (isDuplicate == False)
        5. Not REJECTED

    Args:
        db: Firestore client.
        category: Category to match.
        latitude: New complaint latitude.
        longitude: New complaint longitude.
        radius_meters: Max allowed distance.
        days: Max age of existing complaint.
        exclude_complaint_id: Skip this ID (the one being processed).

    Returns:
        Complaint dict if a duplicate is found, else None.
    """
    from models import COLLECTION_COMPLAINTS

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        # Query only by category (single-field — no composite index needed).
        # All other filters (isDuplicate, createdAt, status) applied in Python.
        candidates = (
            db.collection(COLLECTION_COMPLAINTS)
            .where("category", "==", category)
            .stream()
        )

        for doc in candidates:
            c = doc.to_dict()
            if c.get("id") == exclude_complaint_id:
                continue
            if c.get("isDuplicate"):
                continue
            if c.get("status") == "REJECTED":
                continue
            # Check time window in Python
            created = c.get("createdAt")
            if created is not None:
                if hasattr(created, "tzinfo") and created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if created < cutoff:
                    continue

            try:
                dist = haversine_distance(
                    latitude, longitude,
                    float(c.get("latitude") or 0),
                    float(c.get("longitude") or 0),
                )
            except Exception:
                continue

            if dist <= radius_meters:
                logger.info(
                    f"Duplicate found: existing={c.get('id')}, distance={dist:.1f}m"
                )
                return c

    except Exception as exc:
        logger.error(f"Duplicate detection error: {exc}", exc_info=True)

    return None


# ─── Community Validation Score ───────────────────────────────────────────────

def compute_community_validation_score(reporter_count: int) -> float:
    """
    Compute community validation score based on number of unique reporters.

    Formula: min(1.0, (reporters - 1) * 0.1)
    One reporter = 0.0, two = 0.1, eleven = 1.0.

    Args:
        reporter_count: Total number of unique reporters for the complaint.

    Returns:
        Validation score between 0.0 and 1.0.
    """
    if reporter_count <= 1:
        return 0.0
    return round(min(1.0, (reporter_count - 1) * 0.1), 3)
