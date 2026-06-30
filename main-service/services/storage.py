"""
Main Service — Google Cloud Storage Service
Handles image upload to GCS bucket.
"""
import logging
import os
import uuid
from typing import Optional

logger = logging.getLogger("main-service.storage")


def get_gcs_client():
    """Lazy-load GCS client. On Cloud Run uses Application Default Credentials automatically."""
    from google.cloud import storage as gcs
    # Application Default Credentials are used automatically on Cloud Run.
    # For local dev, set GOOGLE_APPLICATION_CREDENTIALS env var.
    return gcs.Client()


def upload_image_to_gcs(file_obj, original_filename: str) -> Optional[str]:
    """
    Upload an image file object to GCS.

    Args:
        file_obj: File-like object (from Flask request.files).
        original_filename: Original file name to derive extension.

    Returns:
        Public GCS URL string, or None on failure.
    """
    from config import config

    if not config.GCS_BUCKET_NAME:
        logger.warning("GCS_BUCKET_NAME not configured. Skipping image upload.")
        return None

    try:
        ext = os.path.splitext(original_filename)[1].lower() or ".jpg"
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        if ext not in allowed_extensions:
            ext = ".jpg"

        blob_name = f"complaints/{uuid.uuid4()}{ext}"

        client = get_gcs_client()
        bucket = client.bucket(config.GCS_BUCKET_NAME)
        blob = bucket.blob(blob_name)

        file_obj.seek(0)
        blob.upload_from_file(file_obj, content_type=f"image/{ext.lstrip('.')}")

        # Make blob publicly readable
        blob.make_public()

        url = blob.public_url
        logger.info(f"Image uploaded to GCS: {url}")
        return url

    except Exception as exc:
        logger.error(f"GCS upload failed: {exc}", exc_info=True)
        return None


def download_image_from_gcs(gcs_url: str) -> Optional[bytes]:
    """
    Download image bytes from a GCS public URL.

    Args:
        gcs_url: Public GCS URL.

    Returns:
        Image bytes or None on failure.
    """
    try:
        import requests
        response = requests.get(gcs_url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as exc:
        logger.error(f"GCS download failed for {gcs_url}: {exc}", exc_info=True)
        return None
