"""
Main Service — Pub/Sub Publisher
Replaces kafka_producer.py. Publishes complaint-created events to Google Cloud Pub/Sub.
"""
import json
import logging

logger = logging.getLogger("main-service.pubsub_publisher")

_publisher = None
_topic_path = None


def _get_publisher():
    """Lazy singleton Pub/Sub publisher client."""
    global _publisher, _topic_path
    if _publisher is None:
        import os
        from google.cloud import pubsub_v1
        from config import config

        if config.GOOGLE_APPLICATION_CREDENTIALS:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS

        _publisher = pubsub_v1.PublisherClient()
        _topic_path = _publisher.topic_path(config.GCP_PROJECT_ID, config.PUBSUB_TOPIC)
        logger.info(f"Pub/Sub publisher initialised. Topic: {_topic_path}")

    return _publisher, _topic_path


def publish_complaint_event(complaint_id: str) -> bool:
    """
    Publish a complaint-created event to Google Cloud Pub/Sub.

    Publishes only the complaintId as the message payload.
    The processing-service subscribes to this topic and fetches the full
    complaint from Firestore upon receiving the message.

    Args:
        complaint_id: UUID of the newly created complaint.

    Returns:
        True on success, False on failure.
    """
    try:
        publisher, topic_path = _get_publisher()
        message = json.dumps({"complaintId": complaint_id}).encode("utf-8")
        future = publisher.publish(topic_path, data=message)
        message_id = future.result(timeout=10)
        logger.info(
            f"Published Pub/Sub event: complaintId={complaint_id} "
            f"messageId={message_id} topic={topic_path}"
        )
        return True
    except Exception as exc:
        logger.error(
            f"Failed to publish Pub/Sub event for complaint {complaint_id}: {exc}",
            exc_info=True,
        )
        return False
