"""
Processing Service — Priority Calculator
Implements the weighted priority scoring formula using env-var weights.

Formula:
    Praw = wS*S + wC*C + wR*R + wU*U + wV*V
    P = clip(100 × E × Praw, 0, 100)

Where:
    S  = AI-derived severity score (0–1) from Gemini
    C  = Criticality score based on nearby infrastructure (0–1)
    R  = Recurrence / hotspot score (0–1)
    U  = Reporter credibility score (0–1)
    V  = Community validation score (0–1)
    E  = Equity multiplier (from EQUITY_MULTIPLIER env var)
"""
import logging
import math
from typing import Optional

import requests

logger = logging.getLogger("processing-service.priority_calculator")

NEARBY_PLACE_TYPES = ["hospital", "school", "government", "highway", "market"]
CRITICALITY_RADIUS_METERS = 1000


# ─── Criticality Score ────────────────────────────────────────────────────────

def _get_nearby_place_count(lat: float, lng: float, place_type: str, api_key: str) -> int:
    """Query Google Places Nearby Search API for infrastructure count."""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": CRITICALITY_RADIUS_METERS,
        "keyword": place_type,
        "key": api_key,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return len(resp.json().get("results", []))
    except Exception as exc:
        logger.warning(f"Google Places API error for type={place_type}: {exc}")
        return 0


def compute_criticality_score(lat: float, lng: float) -> float:
    """
    Compute criticality score (0–1) based on nearby critical infrastructure.
    Returns 0.5 if GOOGLE_MAPS_API_KEY is not configured.
    """
    from config import config

    if not config.GOOGLE_MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY not set. Using fallback criticality=0.5.")
        return 0.5

    max_possible = len(NEARBY_PLACE_TYPES) * 5
    total_nearby = 0

    for place_type in NEARBY_PLACE_TYPES:
        total_nearby += min(_get_nearby_place_count(lat, lng, place_type, config.GOOGLE_MAPS_API_KEY), 5)

    score = total_nearby / max_possible if max_possible > 0 else 0.5
    return round(min(1.0, max(0.0, score)), 3)


# ─── Recurrence Score ─────────────────────────────────────────────────────────

def compute_recurrence_score(
    db,
    category: str,
    lat: float,
    lng: float,
    radius_meters: float = 1000,
    lookback_days: int = 90,
) -> float:
    """
    Compute recurrence/hotspot score based on similar complaints in the same area.

    Queries Firestore for complaints of the same category within radius_meters
    in the last lookback_days. Score = min(1.0, count / 10).

    Args:
        db: Firestore client.
        category: Complaint category.
        lat, lng: Location.
        radius_meters: Area radius.
        lookback_days: Historical window.

    Returns:
        Score between 0.0 and 1.0.
    """
    from datetime import datetime, timedelta, timezone
    from models import COLLECTION_COMPLAINTS

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    try:
        # Query only by category (single-field — no composite index needed).
        # createdAt range and status filters applied in Python.
        candidates = (
            db.collection(COLLECTION_COMPLAINTS)
            .where("category", "==", category)
            .stream()
        )

        nearby_count = 0
        for doc in candidates:
            c = doc.to_dict()
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
                dist = _haversine(lat, lng, float(c.get("latitude") or 0), float(c.get("longitude") or 0))
                if dist <= radius_meters:
                    nearby_count += 1
            except Exception:
                continue

    except Exception as exc:
        logger.error(f"Recurrence score error: {exc}", exc_info=True)
        return 0.0

    return round(min(1.0, nearby_count / 10.0), 3)


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─── Priority Formula ─────────────────────────────────────────────────────────

def compute_priority_score(
    severity: float,
    criticality: float,
    recurrence: float,
    credibility: float,
    validation: float,
) -> float:
    """
    Compute final priority score (0–100) using the weighted formula.

    P = clip(100 × E × Praw, 0, 100)
    Praw = wS*S + wC*C + wR*R + wU*U + wV*V

    Weights are read from environment variables via config.
    Weights are normalised if they don't sum to exactly 1.0.

    Args:
        severity: Gemini AI severity (0–1)
        criticality: Nearby infrastructure (0–1)
        recurrence: Hotspot recurrence (0–1)
        credibility: Reporter credibility (0–1)
        validation: Community validation (0–1)

    Returns:
        Priority score between 0.0 and 100.0.
    """
    from config import config

    wS = config.WEIGHT_SEVERITY
    wC = config.WEIGHT_CRITICALITY
    wR = config.WEIGHT_RECURRENCE
    wU = config.WEIGHT_CREDIBILITY
    wV = config.WEIGHT_VALIDATION
    E = config.EQUITY_MULTIPLIER

    total_weight = wS + wC + wR + wU + wV
    if total_weight > 0:
        wS /= total_weight
        wC /= total_weight
        wR /= total_weight
        wU /= total_weight
        wV /= total_weight

    praw = wS * severity + wC * criticality + wR * recurrence + wU * credibility + wV * validation
    priority = max(0.0, min(100.0, 100 * E * praw))

    logger.debug(
        f"Priority: S={severity:.3f} C={criticality:.3f} R={recurrence:.3f} "
        f"U={credibility:.3f} V={validation:.3f} → Praw={praw:.3f} P={priority:.2f}"
    )
    return round(priority, 2)
