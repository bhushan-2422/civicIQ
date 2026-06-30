"""
Main Service — Complaints Routes (Firestore)
All persistence via Google Cloud Firestore. No SQL.
"""
import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app

from models import (
    build_complaint_doc,
    build_user_doc,
    complaint_to_dict,
    COLLECTION_COMPLAINTS,
    COLLECTION_USERS,
    COLLECTION_REPORTERS,
    STATUS_VALUES,
    utc_now,
)

logger = logging.getLogger("main-service.complaints")
complaints_bp = Blueprint("complaints", __name__)

VALID_STATUSES = set(STATUS_VALUES)
VALID_SORT_FIELDS = {"createdAt", "priorityScore", "status", "updatedAt"}


def _db():
    return current_app.get_db()


# ─── POST /api/complaints ─────────────────────────────────────────────────────

@complaints_bp.post("/complaints")
def submit_complaint():
    """
    Submit a new civic complaint.

    Form fields:
        name        (str) Reporter full name
        phone       (str) Reporter phone number
        description (str) Complaint description (min 20 chars)
        latitude    (float) GPS latitude
        longitude   (float) GPS longitude
        image       (file, optional) Complaint photo

    Returns:
        201: {success, complaintId, status, message}
        400: {success, errors}
        500: {success, error}
    """
    db = _db()

    try:
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        description = request.form.get("description", "").strip()
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")

        # Validate
        errors = []
        if not name:
            errors.append("name is required")
        if not phone:
            errors.append("phone is required")
        if not description or len(description) < 20:
            errors.append("description is required (min 20 characters)")
        if not latitude:
            errors.append("latitude is required")
        if not longitude:
            errors.append("longitude is required")

        if errors:
            return jsonify({"success": False, "errors": errors}), 400

        try:
            lat = float(latitude)
            lng = float(longitude)
        except (ValueError, TypeError):
            return jsonify({"success": False, "errors": ["latitude and longitude must be numbers"]}), 400

        # ── Upload image to GCS ───────────────────────────────
        image_url = None
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            from services.storage import upload_image_to_gcs
            image_url = upload_image_to_gcs(image_file, image_file.filename)

        # ── Get or create user in Firestore ───────────────────
        user_ref = db.collection(COLLECTION_USERS).document(phone)
        user_snap = user_ref.get()

        if user_snap.exists:
            user_data = user_snap.to_dict()
        else:
            user_data = build_user_doc(name=name, phone=phone)
            user_ref.set(user_data)

        credibility = float(user_data.get("credibilityScore", 0.5))

        # ── Build and save complaint ──────────────────────────
        complaint_doc = build_complaint_doc(
            description=description,
            latitude=lat,
            longitude=lng,
            reporter_name=name,
            reporter_phone=phone,
            reporter_credibility=credibility,
            image_url=image_url,
        )
        complaint_id = complaint_doc["id"]

        db.collection(COLLECTION_COMPLAINTS).document(complaint_id).set(complaint_doc)

        # ── Record reporter link ──────────────────────────────
        reporter_key = f"{complaint_id}_{phone}"
        db.collection(COLLECTION_REPORTERS).document(reporter_key).set({
            "complaintId": complaint_id,
            "userPhone": phone,
            "reportedAt": utc_now(),
        })

        # ── Publish Pub/Sub event ─────────────────────────────
        try:
            from services.pubsub_publisher import publish_complaint_event
            publish_complaint_event(complaint_id)
        except Exception as pub_exc:
            logger.warning(f"Pub/Sub publish failed (complaint saved): {pub_exc}")

        logger.info(f"Complaint created: {complaint_id}")
        return jsonify({
            "success": True,
            "complaintId": complaint_id,
            "status": "PROCESSING",
            "message": "Complaint submitted successfully. Processing will begin shortly.",
        }), 201

    except Exception as exc:
        logger.error(f"Error submitting complaint: {exc}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ─── GET /api/complaints ──────────────────────────────────────────────────────

@complaints_bp.get("/complaints")
def list_complaints():
    """
    List all complaints with optional filtering, searching, sorting and pagination.

    Query params:
        status      (str)  Filter by status
        department  (str)  Filter by department
        category    (str)  Filter by category
        search      (str)  Keyword search in description/summary/reporterName
        sort        (str)  createdAt | priorityScore | status | updatedAt
        order       (str)  asc | desc (default: desc)
        page        (int)  Page number (default: 1)
        per_page    (int)  Items per page (default: 20, max: 100)

    Returns:
        200: {success, data, pagination}
    """
    db = _db()

    try:
        status_filter = (request.args.get("status") or "").upper() or None
        department_filter = (request.args.get("department") or "").upper() or None
        category_filter = (request.args.get("category") or "").upper() or None
        search = (request.args.get("search") or "").strip().lower()
        sort_field = request.args.get("sort", "createdAt")
        order = request.args.get("order", "desc").lower()
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))

        if sort_field not in VALID_SORT_FIELDS:
            sort_field = "createdAt"

        # Stream entire collection then filter/sort in Python.
        # This avoids Firestore composite index requirements for any combination
        # of where() + order_by() filters the officer dashboard might use.
        docs = db.collection(COLLECTION_COMPLAINTS).stream()
        all_complaints = [d.to_dict() for d in docs]

        # Apply filters in Python
        if status_filter:
            all_complaints = [c for c in all_complaints if c.get("status") == status_filter]
        if department_filter:
            all_complaints = [c for c in all_complaints if c.get("department") == department_filter]
        if category_filter:
            all_complaints = [c for c in all_complaints if c.get("category") == category_filter]

        # Client-side search (Firestore has no full-text search)
        if search:
            all_complaints = [
                c for c in all_complaints
                if search in (c.get("description") or "").lower()
                or search in (c.get("summary") or "").lower()
                or search in (c.get("reporterName") or "").lower()
            ]

        # Sort in Python
        reverse = (order == "desc")
        all_complaints.sort(key=lambda c: (c.get(sort_field) is None, c.get(sort_field)), reverse=reverse)

        total = len(all_complaints)
        start = (page - 1) * per_page
        paginated = all_complaints[start: start + per_page]

        return jsonify({
            "success": True,
            "data": [complaint_to_dict(c) for c in paginated],
            "pagination": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": max(1, (total + per_page - 1) // per_page),
            },
        }), 200

    except Exception as exc:
        logger.error(f"Error listing complaints: {exc}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ─── GET /api/complaints/<id> ─────────────────────────────────────────────────

@complaints_bp.get("/complaints/<complaint_id>")
def get_complaint(complaint_id: str):
    """
    Get a single complaint by ID.

    Returns:
        200: {success, data}
        404: {success, error}
    """
    db = _db()

    try:
        doc = db.collection(COLLECTION_COMPLAINTS).document(complaint_id).get()
        if not doc.exists:
            return jsonify({"success": False, "error": "Complaint not found"}), 404

        data = complaint_to_dict(doc.to_dict())

        # Reporter count stored on the document itself (updated on duplicate detection)
        return jsonify({"success": True, "data": data}), 200

    except Exception as exc:
        logger.error(f"Error fetching complaint {complaint_id}: {exc}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ─── PATCH /api/complaints/<id>/status ───────────────────────────────────────

@complaints_bp.patch("/complaints/<complaint_id>/status")
def update_status(complaint_id: str):
    """
    Update complaint status.

    JSON body:
        status (str): VALID | IN_PROGRESS | RESOLVED | REJECTED

    Returns:
        200: {success, data}
        400: {success, error}
        404: {success, error}
    """
    db = _db()

    try:
        body = request.get_json(force=True) or {}
        new_status = (body.get("status") or "").upper()

        if new_status not in VALID_STATUSES:
            return jsonify({
                "success": False,
                "error": f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
            }), 400

        ref = db.collection(COLLECTION_COMPLAINTS).document(complaint_id)
        snap = ref.get()
        if not snap.exists:
            return jsonify({"success": False, "error": "Complaint not found"}), 404

        complaint = snap.to_dict()
        old_status = complaint.get("status")

        ref.update({"status": new_status, "updatedAt": utc_now()})

        # Update reporter credibility
        _update_reporter_credibility(db, complaint.get("reporterPhone"), new_status, old_status)

        # Fetch updated document
        updated = ref.get().to_dict()
        logger.info(f"Complaint {complaint_id} status: {old_status} → {new_status}")
        return jsonify({"success": True, "data": complaint_to_dict(updated)}), 200

    except Exception as exc:
        logger.error(f"Error updating complaint {complaint_id}: {exc}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


def _update_reporter_credibility(db, phone: str, new_status: str, old_status: str):
    """Adjust reporter credibility score in Firestore based on complaint outcome."""
    if not phone or new_status == old_status:
        return

    user_ref = db.collection(COLLECTION_USERS).document(phone)
    snap = user_ref.get()
    if not snap.exists:
        return

    user = snap.to_dict()
    score = float(user.get("credibilityScore", 0.5))
    updates = {}

    if new_status == "VALID":
        updates["credibilityScore"] = round(min(1.0, score + 0.05), 3)
        updates["validatedCount"] = (user.get("validatedCount") or 0) + 1
    elif new_status == "REJECTED":
        updates["credibilityScore"] = round(max(0.0, score - 0.05), 3)
        updates["rejectedCount"] = (user.get("rejectedCount") or 0) + 1
    elif new_status == "RESOLVED":
        updates["credibilityScore"] = round(min(1.0, score + 0.02), 3)

    if updates:
        updates["updatedAt"] = utc_now()
        user_ref.update(updates)


# ─── POST /api/complaints/<id>/assign ────────────────────────────────────────

@complaints_bp.post("/complaints/<complaint_id>/assign")
def assign_worker(complaint_id: str):
    """
    Assign a field worker to a complaint and send SMS via Twilio.

    JSON body:
        workerName  (str) Name of the assigned worker
        workerPhone (str) Worker phone number in E.164 format

    Returns:
        200: {success, smsSent, message, data}
        400: {success, error}
        404: {success, error}
    """
    db = _db()

    try:
        body = request.get_json(force=True) or {}
        worker_name = (body.get("workerName") or "").strip()
        worker_phone = (body.get("workerPhone") or "").strip()

        if not worker_name or not worker_phone:
            return jsonify({"success": False, "error": "workerName and workerPhone are required"}), 400

        ref = db.collection(COLLECTION_COMPLAINTS).document(complaint_id)
        snap = ref.get()
        if not snap.exists:
            return jsonify({"success": False, "error": "Complaint not found"}), 404

        complaint = snap.to_dict()

        # Set status to IN_PROGRESS if currently VALID
        if complaint.get("status") == "VALID":
            ref.update({"status": "IN_PROGRESS", "updatedAt": utc_now()})
            complaint["status"] = "IN_PROGRESS"

        # Send Twilio SMS
        from services.twilio_service import send_assignment_sms
        sms_sent = send_assignment_sms(
            worker_name=worker_name,
            worker_phone=worker_phone,
            complaint_id=complaint_id,
            complaint_summary=complaint.get("summary") or complaint.get("description", "")[:100],
            category=complaint.get("category") or "UNKNOWN",
            priority_score=float(complaint.get("priorityScore") or 0),
            latitude=float(complaint.get("latitude") or 0),
            longitude=float(complaint.get("longitude") or 0),
            status=complaint.get("status", "IN_PROGRESS"),
        )

        return jsonify({
            "success": True,
            "smsSent": sms_sent,
            "message": f"Worker {worker_name} assigned successfully.",
            "data": complaint_to_dict(ref.get().to_dict()),
        }), 200

    except Exception as exc:
        logger.error(f"Error assigning worker for {complaint_id}: {exc}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500
