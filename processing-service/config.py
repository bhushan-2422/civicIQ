"""
Processing Service — Configuration
All configuration loaded from environment variables. No hardcoded values.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Flask ─────────────────────────────────────────────────
    FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5001"))

    # ── Google Cloud ──────────────────────────────────────────
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    FIRESTORE_DATABASE: str = os.getenv("FIRESTORE_DATABASE", "(default)")

    # ── Google Cloud Storage ──────────────────────────────────
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "")

    # ── Google Cloud Pub/Sub ──────────────────────────────────
    PUBSUB_SUBSCRIPTION: str = os.getenv("PUBSUB_SUBSCRIPTION", "complaint-created-sub")

    # ── Google Gemini ──────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # ── Google Maps ───────────────────────────────────────────
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

    # ── Twilio ────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")

    # ── Duplicate Detection ───────────────────────────────────
    DUPLICATE_RADIUS_METERS: float = float(os.getenv("DUPLICATE_RADIUS_METERS", "500"))
    DUPLICATE_DAYS: int = int(os.getenv("DUPLICATE_DAYS", "30"))

    # ── Priority Weights ──────────────────────────────────────
    WEIGHT_SEVERITY: float = float(os.getenv("PRIORITY_WEIGHT_SEVERITY", "0.35"))
    WEIGHT_CRITICALITY: float = float(os.getenv("PRIORITY_WEIGHT_CRITICALITY", "0.20"))
    WEIGHT_RECURRENCE: float = float(os.getenv("PRIORITY_WEIGHT_RECURRENCE", "0.15"))
    WEIGHT_CREDIBILITY: float = float(os.getenv("PRIORITY_WEIGHT_CREDIBILITY", "0.15"))
    WEIGHT_VALIDATION: float = float(os.getenv("PRIORITY_WEIGHT_VALIDATION", "0.15"))
    EQUITY_MULTIPLIER: float = float(os.getenv("EQUITY_MULTIPLIER", "1.0"))


config = Config()
