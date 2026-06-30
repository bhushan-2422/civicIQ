"""
Main Service — Users Routes (Firestore)
Community heroes leaderboard from Firestore users collection.
"""
import logging
from flask import Blueprint, request, jsonify, current_app

from models import COLLECTION_USERS

logger = logging.getLogger("main-service.users")
users_bp = Blueprint("users", __name__)


def _db():
    return current_app.get_db()


@users_bp.get("/users/leaderboard")
def leaderboard():
    """
    Get top community heroes ranked by validated complaints.

    Query params:
        limit (int): Number of top users to return (default: 10, max: 50)

    Returns:
        200: {success, data: [{rank, name, phone, validatedCount, credibilityScore, badge}]}
    """
    db = _db()

    try:
        limit = min(50, max(1, int(request.args.get("limit", 10))))

        # Stream all users and sort in Python to avoid composite index requirement.
        docs = db.collection(COLLECTION_USERS).stream()
        users_all = [d.to_dict() for d in docs]

        # Filter and sort in Python
        users = sorted(
            [u for u in users_all if u.get("validatedCount", 0) > 0],
            key=lambda u: u.get("validatedCount", 0),
            reverse=True,
        )[:limit]

        result = []
        for rank, user in enumerate(users, start=1):
            phone = user.get("phone", "")
            masked_phone = phone[-4:].rjust(10, "*") if len(phone) >= 4 else "****"
            result.append({
                "rank": rank,
                "name": user.get("name"),
                "phone": masked_phone,
                "validatedCount": user.get("validatedCount", 0),
                "credibilityScore": float(user.get("credibilityScore", 0.5)),
                "badge": _get_badge(user.get("validatedCount", 0)),
            })

        return jsonify({"success": True, "data": result}), 200

    except Exception as exc:
        logger.error(f"Leaderboard error: {exc}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


def _get_badge(validated_count: int) -> str:
    if validated_count >= 20:
        return "🏆 Champion"
    elif validated_count >= 10:
        return "🥇 Gold"
    elif validated_count >= 5:
        return "🥈 Silver"
    elif validated_count >= 2:
        return "🥉 Bronze"
    return "⭐ Contributor"
