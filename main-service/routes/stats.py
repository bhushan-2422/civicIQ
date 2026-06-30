"""
Main Service — Statistics Routes (Firestore)
Aggregated stats computed client-side from Firestore documents.
"""
import logging
from collections import defaultdict
from flask import Blueprint, jsonify, current_app

from models import COLLECTION_COMPLAINTS

logger = logging.getLogger("main-service.stats")
stats_bp = Blueprint("stats", __name__)


def _db():
    return current_app.get_db()


@stats_bp.get("/stats")
def overall_stats():
    """
    Get overall complaint statistics.

    Returns:
        200: {success, data: {total, pending, resolved, rejected, highPriority, averagePriority}}
    """
    db = _db()
    try:
        docs = [d.to_dict() for d in db.collection(COLLECTION_COMPLAINTS).stream()]

        total = len(docs)
        pending = sum(1 for d in docs if d.get("status") in {"PROCESSING", "VALID", "IN_PROGRESS"})
        resolved = sum(1 for d in docs if d.get("status") == "RESOLVED")
        rejected = sum(1 for d in docs if d.get("status") == "REJECTED")
        high_priority = sum(1 for d in docs if float(d.get("priorityScore") or 0) >= 70)

        scores = [float(d.get("priorityScore") or 0) for d in docs]
        avg_priority = round(sum(scores) / len(scores), 2) if scores else 0.0

        return jsonify({
            "success": True,
            "data": {
                "total": total,
                "pending": pending,
                "resolved": resolved,
                "rejected": rejected,
                "highPriority": high_priority,
                "averagePriority": avg_priority,
            },
        }), 200

    except Exception as exc:
        logger.error(f"Stats error: {exc}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


@stats_bp.get("/stats/department")
def department_stats():
    """
    Get complaint counts grouped by department.

    Returns:
        200: {success, data: [{department, count}]}
    """
    db = _db()
    try:
        docs = [d.to_dict() for d in db.collection(COLLECTION_COMPLAINTS).stream()]
        counts: dict = defaultdict(int)
        for d in docs:
            dept = d.get("department")
            if dept:
                counts[dept] += 1

        data = [{"department": k, "count": v} for k, v in counts.items()]
        data.sort(key=lambda x: x["count"], reverse=True)
        return jsonify({"success": True, "data": data}), 200

    except Exception as exc:
        logger.error(f"Department stats error: {exc}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


@stats_bp.get("/stats/category")
def category_stats():
    """
    Get complaint counts grouped by category.

    Returns:
        200: {success, data: [{category, count}]}
    """
    db = _db()
    try:
        docs = [d.to_dict() for d in db.collection(COLLECTION_COMPLAINTS).stream()]
        counts: dict = defaultdict(int)
        for d in docs:
            cat = d.get("category")
            if cat:
                counts[cat] += 1

        data = [{"category": k, "count": v} for k, v in counts.items()]
        data.sort(key=lambda x: x["count"], reverse=True)
        return jsonify({"success": True, "data": data}), 200

    except Exception as exc:
        logger.error(f"Category stats error: {exc}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


@stats_bp.get("/stats/hotspots")
def hotspot_stats():
    """
    Get all complaint locations for map hotspot visualisation.

    Returns:
        200: {success, data: [{id, lat, lng, priority, category, status}]}
    """
    db = _db()
    try:
        docs = [d.to_dict() for d in db.collection(COLLECTION_COMPLAINTS).stream()]
        data = [
            {
                "id": d.get("id"),
                "lat": float(d.get("latitude") or 0),
                "lng": float(d.get("longitude") or 0),
                "priority": float(d.get("priorityScore") or 0),
                "category": d.get("category"),
                "status": d.get("status"),
            }
            for d in docs
            if d.get("latitude") is not None and d.get("longitude") is not None
        ]
        return jsonify({"success": True, "data": data}), 200

    except Exception as exc:
        logger.error(f"Hotspot stats error: {exc}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500
