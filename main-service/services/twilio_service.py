"""
Main Service — Twilio SMS Service
Sends SMS notifications when a worker is assigned to a complaint.
"""
import logging
from typing import Optional

logger = logging.getLogger("main-service.twilio_service")


def send_assignment_sms(
    worker_name: str,
    worker_phone: str,
    complaint_id: str,
    complaint_summary: str,
    category: str,
    priority_score: float,
    latitude: float,
    longitude: float,
    status: str,
) -> bool:
    """
    Send an SMS to the assigned worker with complaint details.

    Args:
        worker_name: Name of the worker being assigned.
        worker_phone: Phone number of the worker (E.164 format, e.g. +919876543210).
        complaint_id: Complaint UUID.
        complaint_summary: AI-generated summary.
        category: Complaint category.
        priority_score: Computed priority score (0–100).
        latitude: Complaint location latitude.
        longitude: Complaint location longitude.
        status: Current complaint status.

    Returns:
        True on success, False on failure.
    """
    from config import config

    if not all([config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN, config.TWILIO_PHONE_NUMBER]):
        logger.warning("Twilio credentials not configured. SMS will not be sent.")
        return False

    try:
        from twilio.rest import Client
        client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

        maps_link = f"https://maps.google.com/?q={latitude},{longitude}"
        body = (
            f"🏙️ CIVIC PLATFORM — WORK ASSIGNMENT\n\n"
            f"Hello {worker_name},\n\n"
            f"You have been assigned a complaint:\n"
            f"📋 ID: {complaint_id[:8].upper()}\n"
            f"🏷️ Category: {category}\n"
            f"📝 Summary: {complaint_summary or 'N/A'}\n"
            f"⚡ Priority: {priority_score:.1f}/100\n"
            f"🔄 Status: {status}\n"
            f"📍 Location: {maps_link}\n\n"
            f"Please report to the site promptly.\n"
            f"— Civic Intelligence Platform"
        )

        message = client.messages.create(
            body=body,
            from_=config.TWILIO_PHONE_NUMBER,
            to=worker_phone,
        )
        logger.info(f"SMS sent to {worker_phone}. SID: {message.sid}")
        return True

    except Exception as exc:
        logger.error(f"Twilio SMS failed: {exc}", exc_info=True)
        return False
