"""
Processing Service — Google Cloud Pub/Sub Subscriber
Replaces consumer.py (Kafka). Subscribes to the complaint-created topic
and orchestrates the full AI processing pipeline via Firestore.

Pipeline:
    1. Receive complaintId from Pub/Sub message
    2. Fetch complaint document from Firestore
    3. Download image from GCS URL
    4. Call Gemini API → {category, department, severity, estimatedCost, estimatedDuration, summary}
    5. Perform duplicate detection (geo + category + time window) against Firestore
    6. If duplicate → associate reporter, increase validation score, recalculate priority, update Firestore
    7. If not duplicate → compute criticality, recurrence, priority; update Firestore as VALID
"""
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("processing-service.subscriber")


# ─── Firestore client ─────────────────────────────────────────────────────────

_db = None


def _get_db():
    """Lazy Firestore client for the subscriber thread."""
    global _db
    if _db is None:
        from google.cloud import firestore
        from config import config

        if config.GOOGLE_APPLICATION_CREDENTIALS:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS

        kwargs = {"project": config.GCP_PROJECT_ID} if config.GCP_PROJECT_ID else {}
        if config.FIRESTORE_DATABASE and config.FIRESTORE_DATABASE != "(default)":
            kwargs["database"] = config.FIRESTORE_DATABASE

        _db = firestore.Client(**kwargs)
        logger.info("Subscriber Firestore client initialised.")
    return _db


# ─── Core processing pipeline ─────────────────────────────────────────────────

def process_complaint(complaint_id: str) -> bool:
    """
    Full AI processing pipeline for a single complaint.

    Args:
        complaint_id: Firestore document ID of the complaint to process.

    Returns:
        True on success, False on failure.
    """
    db = _get_db()

    try:
        from models import COLLECTION_COMPLAINTS, COLLECTION_USERS, COLLECTION_REPORTERS, utc_now
        from services.gemini_service import analyze_complaint
        from services.duplicate_detector import find_duplicate, compute_community_validation_score
        from services.priority_calculator import (
            compute_criticality_score,
            compute_recurrence_score,
            compute_priority_score,
        )
        from services.storage import download_image_from_url
        from config import config

        # ── 1. Fetch complaint from Firestore ────────────────────
        doc_ref = db.collection(COLLECTION_COMPLAINTS).document(complaint_id)
        snap = doc_ref.get()
        if not snap.exists:
            logger.error(f"Complaint {complaint_id} not found in Firestore.")
            return False

        complaint = snap.to_dict()
        logger.info(f"Processing complaint: {complaint_id}")

        # ── 2. Download image ────────────────────────────────────
        image_bytes: Optional[bytes] = None
        image_url = complaint.get("imageUrl")
        if image_url:
            image_bytes = download_image_from_url(image_url)
            if image_bytes:
                logger.info(f"Image downloaded: {len(image_bytes)} bytes")
            else:
                logger.warning(f"Could not download image for {complaint_id}")

        # ── 3. Gemini AI analysis ─────────────────────────────────
        ai_result = analyze_complaint(
            description=complaint.get("description", ""),
            image_bytes=image_bytes,
        )
        logger.info(f"Gemini result: {ai_result}")

        category = ai_result["category"]
        department = ai_result["department"]
        severity = ai_result["severity"]
        estimated_cost = ai_result["estimatedCost"]
        estimated_duration = ai_result["estimatedDuration"]
        summary = ai_result["summary"]

        lat = float(complaint.get("latitude") or 0)
        lng = float(complaint.get("longitude") or 0)

        # ── 4. Duplicate detection ───────────────────────────────
        existing_complaint = find_duplicate(
            db=db,
            category=category,
            latitude=lat,
            longitude=lng,
            radius_meters=config.DUPLICATE_RADIUS_METERS,
            days=config.DUPLICATE_DAYS,
            exclude_complaint_id=complaint_id,
        )

        if existing_complaint:
            existing_id = existing_complaint.get("id")
            logger.info(
                f"Complaint {complaint_id} is a duplicate of {existing_id}. "
                "Associating reporter."
            )

            reporter_phone = complaint.get("reporterPhone")
            existing_ref = db.collection(COLLECTION_COMPLAINTS).document(existing_id)

            # Associate reporter — use phone as key to prevent dupes
            if reporter_phone:
                reporter_key = f"{existing_id}_{reporter_phone}"
                reporter_ref = db.collection(COLLECTION_REPORTERS).document(reporter_key)
                if not reporter_ref.get().exists:
                    reporter_ref.set({
                        "complaintId": existing_id,
                        "userPhone": reporter_phone,
                        "reportedAt": utc_now(),
                    })

            # Count total unique reporters on the parent complaint
            reporters = (
                db.collection(COLLECTION_REPORTERS)
                .where("complaintId", "==", existing_id)
                .stream()
            )
            reporter_count = sum(1 for _ in reporters) + 1  # +1 for just-added

            # Recompute community validation and priority for parent
            new_validation = compute_community_validation_score(reporter_count)
            existing_data = existing_complaint

            new_priority = compute_priority_score(
                severity=float(existing_data.get("severityScore") or severity),
                criticality=compute_criticality_score(
                    lat=float(existing_data.get("latitude") or lat),
                    lng=float(existing_data.get("longitude") or lng),
                ),
                recurrence=compute_recurrence_score(
                    db=db,
                    category=existing_data.get("category") or category,
                    lat=float(existing_data.get("latitude") or lat),
                    lng=float(existing_data.get("longitude") or lng),
                ),
                credibility=float(existing_data.get("reporterCredibility") or 0.5),
                validation=new_validation,
            )

            # Update parent complaint
            existing_ref.update({
                "communityValidation": new_validation,
                "priorityScore": new_priority,
                "reporterCount": reporter_count,
                "updatedAt": utc_now(),
            })

            # Mark current complaint as duplicate and auto-reject it
            doc_ref.update({
                "isDuplicate": True,
                "parentComplaintId": existing_id,
                "category": category,
                "department": department,
                "severityScore": severity,
                "summary": summary,
                "status": "REJECTED",
                "updatedAt": utc_now(),
            })

            logger.info(
                f"Duplicate processed. Parent {existing_id} "
                f"priority updated to {new_priority:.2f}, validation={new_validation:.3f}"
            )
            return True

        # ── 5. Not duplicate — full processing ──────────────────
        credibility = float(complaint.get("reporterCredibility") or 0.5)
        current_validation = float(complaint.get("communityValidation") or 0.0)

        criticality = compute_criticality_score(lat=lat, lng=lng)
        recurrence = compute_recurrence_score(db=db, category=category, lat=lat, lng=lng)

        priority = compute_priority_score(
            severity=severity,
            criticality=criticality,
            recurrence=recurrence,
            credibility=credibility,
            validation=current_validation,
        )

        # ── 6. Update complaint in Firestore ─────────────────────
        doc_ref.update({
            "category": category,
            "department": department,
            "severityScore": severity,
            "estimatedCost": estimated_cost,
            "estimatedDuration": estimated_duration,
            "summary": summary,
            "priorityScore": priority,
            "status": "VALID",
            "updatedAt": utc_now(),
        })

        logger.info(
            f"Complaint {complaint_id} processed: "
            f"category={category} priority={priority:.2f} status=VALID"
        )
        return True

    except Exception as exc:
        logger.error(f"Error processing complaint {complaint_id}: {exc}", exc_info=True)
        return False


# ─── Pub/Sub subscriber ───────────────────────────────────────────────────────

def _message_callback(message):
    """
    Pub/Sub push callback. Called for each received message.
    Acknowledges the message after processing (success or failure).
    """
    try:
        payload = json.loads(message.data.decode("utf-8"))
        complaint_id = payload.get("complaintId")

        if not complaint_id:
            logger.warning(f"Received Pub/Sub message without complaintId: {payload}")
            message.ack()
            return

        logger.info(f"Received Pub/Sub event: complaintId={complaint_id}")
        success = process_complaint(complaint_id)

        if success:
            message.ack()
            logger.info(f"Complaint {complaint_id} processed and acked.")
        else:
            # Nack to allow redelivery for transient failures
            message.nack()
            logger.error(f"Failed to process {complaint_id}. Message nacked for redelivery.")

    except Exception as exc:
        logger.error(f"Error handling Pub/Sub message: {exc}", exc_info=True)
        message.nack()


def start_subscriber():
    """
    Start the Pub/Sub subscriber loop.
    Runs in a blocking loop. Call from a background thread.
    """
    from google.cloud import pubsub_v1
    from config import config

    if config.GOOGLE_APPLICATION_CREDENTIALS:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS

    subscription_path = (
        f"projects/{config.GCP_PROJECT_ID}/subscriptions/{config.PUBSUB_SUBSCRIPTION}"
    )

    logger.info(f"Starting Pub/Sub subscriber: {subscription_path}")

    while True:
        try:
            subscriber = pubsub_v1.SubscriberClient()
            streaming_pull_future = subscriber.subscribe(
                subscription_path, callback=_message_callback
            )
            logger.info("Pub/Sub subscriber connected. Waiting for messages...")

            with subscriber:
                streaming_pull_future.result()  # Blocks indefinitely

        except Exception as exc:
            logger.error(f"Pub/Sub subscriber error: {exc}. Retrying in 10s...", exc_info=True)
            time.sleep(10)


def start_subscriber_thread() -> threading.Thread:
    """Start the Pub/Sub subscriber in a background daemon thread."""
    thread = threading.Thread(target=start_subscriber, daemon=True, name="pubsub-subscriber")
    thread.start()
    logger.info("Pub/Sub subscriber thread started.")
    return thread
