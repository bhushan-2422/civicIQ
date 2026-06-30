"""
Processing Service — GCS Storage (image download)
"""
import logging
from typing import Optional

import requests

logger = logging.getLogger("processing-service.storage")


def download_image_from_url(url: str) -> Optional[bytes]:
    """
    Download image bytes from a public URL (GCS or any URL).

    Args:
        url: Public image URL.

    Returns:
        Image bytes, or None on failure.
    """
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception as exc:
        logger.error(f"Failed to download image from {url}: {exc}", exc_info=True)
        return None
