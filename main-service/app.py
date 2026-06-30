"""
Main Service — Flask Application Entry Point
Uses Firestore for persistence. No SQL, no SQLAlchemy.
"""
import logging
import os
from flask import Flask
from flask_cors import CORS

from config import config

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main-service")


# ─── Firestore Client (lazy singleton) ───────────────────────────────────────
_db = None


def get_db():
    """Return the shared Firestore client, initialising it on first call."""
    global _db
    if _db is None:
        from google.cloud import firestore

        if config.GOOGLE_APPLICATION_CREDENTIALS:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS

        kwargs = {"project": config.GCP_PROJECT_ID} if config.GCP_PROJECT_ID else {}
        if config.FIRESTORE_DATABASE and config.FIRESTORE_DATABASE != "(default)":
            kwargs["database"] = config.FIRESTORE_DATABASE

        _db = firestore.Client(**kwargs)
        logger.info("Firestore client initialised.")
    return _db


# ─── App Factory ──────────────────────────────────────────────────────────────
def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY

    CORS(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}})

    # Expose Firestore client via app context
    app.get_db = get_db  # type: ignore[attr-defined]

    # Register blueprints
    from routes.complaints import complaints_bp
    from routes.users import users_bp
    from routes.stats import stats_bp

    app.register_blueprint(complaints_bp, url_prefix="/api")
    app.register_blueprint(users_bp, url_prefix="/api")
    app.register_blueprint(stats_bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "main-service"}, 200

    return app


# ─── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    logger.info(f"Starting main-service on port {config.FLASK_PORT}")
    app.run(
        host="0.0.0.0",
        port=config.FLASK_PORT,
        debug=(config.FLASK_ENV == "development"),
    )
