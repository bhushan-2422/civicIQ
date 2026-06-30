"""
Processing Service — Flask Application + Predictive Dashboard API
Starts Pub/Sub subscriber in a background thread; exposes health and predictions endpoints.
Uses Firestore for all data. No SQL, no SQLAlchemy.
"""
import logging
import os
from flask import Flask, jsonify
from flask_cors import CORS

from config import config

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("processing-service")


# ─── Firestore client (lazy singleton) ───────────────────────────────────────
_db = None


def get_db():
    """Return the shared Firestore client, initialising on first call."""
    global _db
    if _db is None:
        from google.cloud import firestore

        if config.GOOGLE_APPLICATION_CREDENTIALS:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS

        kwargs = {"project": config.GCP_PROJECT_ID} if config.GCP_PROJECT_ID else {}
        if config.FIRESTORE_DATABASE and config.FIRESTORE_DATABASE != "(default)":
            kwargs["database"] = config.FIRESTORE_DATABASE

        _db = firestore.Client(**kwargs)
        logger.info("Processing-service Firestore client initialised.")
    return _db


# ─── App Factory ──────────────────────────────────────────────────────────────
def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "processing-service"}, 200

    @app.get("/api/predictions")
    def predictions():
        """
        Rule-based predictive maintenance analysis.
        Analyses recent Firestore complaint patterns to generate actionable predictions.

        Returns:
            200: {success, data: [{category, complaintCount, centerLat, centerLng,
                                   probability, riskLevel, riskColor,
                                   averagePriority, recommendation}],
                  generatedAt}
        """
        from collections import defaultdict
        from datetime import datetime, timedelta, timezone
        from models import COLLECTION_COMPLAINTS
        from services.duplicate_detector import _haversine

        db = get_db()
        try:
            cutoff_90 = datetime.now(timezone.utc) - timedelta(days=90)

            # Fetch recent complaints — filter REJECTED in Python to avoid
            # requiring a Firestore composite index on (createdAt, status)
            docs = (
                db.collection(COLLECTION_COMPLAINTS)
                .where("createdAt", ">=", cutoff_90)
                .stream()
            )

            recent = [
                d.to_dict() for d in docs
                if d.to_dict().get("category") and d.to_dict().get("status") != "REJECTED"
            ]

            by_category: dict = defaultdict(list)
            for c in recent:
                by_category[c["category"]].append(c)

            predictions_list = []

            for category, complaints in by_category.items():
                if len(complaints) < 2:
                    continue

                lats = [float(c.get("latitude") or 0) for c in complaints]
                lngs = [float(c.get("longitude") or 0) for c in complaints]
                center_lat = sum(lats) / len(lats)
                center_lng = sum(lngs) / len(lngs)
                avg_priority = sum(float(c.get("priorityScore") or 0) for c in complaints) / len(complaints)

                frequency = len(complaints)
                probability = round(min(0.95, frequency / 20.0), 2)

                if probability >= 0.7:
                    risk_level, risk_color = "HIGH", "#dc2626"
                elif probability >= 0.4:
                    risk_level, risk_color = "MEDIUM", "#d97706"
                else:
                    risk_level, risk_color = "LOW", "#16a34a"

                predictions_list.append({
                    "category": category,
                    "complaintCount": frequency,
                    "centerLat": round(center_lat, 6),
                    "centerLng": round(center_lng, 6),
                    "probability": probability,
                    "riskLevel": risk_level,
                    "riskColor": risk_color,
                    "averagePriority": round(avg_priority, 1),
                    "recommendation": _get_recommendation(category, frequency),
                })

            predictions_list.sort(key=lambda x: x["probability"], reverse=True)

            return jsonify({
                "success": True,
                "data": predictions_list,
                "generatedAt": datetime.now(timezone.utc).isoformat(),
            }), 200

        except Exception as exc:
            logger.error(f"Predictions error: {exc}", exc_info=True)
            return jsonify({"success": False, "error": "Internal server error"}), 500

    return app


def _get_recommendation(category: str, count: int) -> str:
    recommendations = {
        "ROAD_DAMAGE": f"Schedule preventive road inspection and resurfacing for {count} reported sections.",
        "WATER_LEAKAGE": f"Conduct pipeline integrity checks — {count} leaks indicate systemic issues.",
        "STREETLIGHT": f"Replace aging streetlight infrastructure in the affected zone ({count} reports).",
        "TRAFFIC_SIGNAL": f"Audit traffic signal maintenance schedules — {count} failures detected.",
        "SEWERAGE": f"Perform comprehensive sewer line cleaning and blockage clearance ({count} incidents).",
        "GARBAGE": f"Increase waste collection frequency in this zone — {count} disposal issues.",
        "TREE_FALL": f"Tree risk assessment needed — {count} incidents suggest weakened root structures.",
        "OTHER": f"General civic maintenance review recommended ({count} unclassified complaints).",
    }
    return recommendations.get(category, f"{count} complaints require attention.")


# ─── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Start Pub/Sub subscriber thread
    from consumer import start_subscriber_thread
    start_subscriber_thread()

    app = create_app()
    logger.info(f"Starting processing-service on port {config.FLASK_PORT}")
    app.run(
        host="0.0.0.0",
        port=config.FLASK_PORT,
        debug=(config.FLASK_ENV == "development"),
        use_reloader=False,  # Disable reloader — conflicts with subscriber thread
    )
