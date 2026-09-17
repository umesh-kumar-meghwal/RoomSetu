"""
routes/admin.py
Superuser moderation, KYC approvals, student/landlord account suspensions, and audit logs.
"""
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from middleware.auth_guard import login_required
from middleware.role_guard import role_required
from services.supabase_client import get_service_client
from services.storage_service import StorageService
from utils.validators import sanitize_string
from config import Config

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/admin")


def _record_audit_log(action: str, entity_type: str, entity_id: str | None, metadata: dict):
    """Internal helper to write append-only records to audit_logs."""
    try:
        service = get_service_client()
        ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
        if ip_addr and "," in ip_addr:
            ip_addr = ip_addr.split(",")[0].strip()

        service.table("audit_logs").insert({
            "actor_id": session.get("user_id"),
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata": metadata,
            "ip_address": ip_addr
        }).execute()
    except Exception as exc:
        logger.error(f"Audit log recording error: {exc}")


@admin_bp.route("/dashboard")
@login_required
@role_required("ADMIN")
def dashboard():
    """Main administrative dashboard displaying platform metrics and pending queues."""
    service = get_service_client()

    # User metrics
    users_res = service.table("profiles").select("role, account_status").execute()
    users_data = users_res.data or []

    total_students = sum(1 for u in users_data if u.get("role") == "STUDENT")
    total_landlords = sum(1 for u in users_data if u.get("role") == "LANDLORD")
    suspended_users = sum(1 for u in users_data if u.get("account_status") == "SUSPENDED")

    # Pending KYC Verifications count
    pending_kyc_res = service.table("landlord_verifications").select("id", count="exact").eq("verification_status",
                                                                                             "PENDING_REVIEW").execute()
    pending_kyc_count = pending_kyc_res.count or 0

    # Total properties count
    props_res = service.table("properties").select("id, publishing_status").execute()
    total_properties = len(props_res.data or [])
    published_properties = sum(1 for p in (props_res.data or []) if p.get("publishing_status") == "PUBLISHED")

    # Pending reports count
    reports_res = service.table("reports").select("id", count="exact").eq("status", "PENDING").execute()
    pending_reports_count = reports_res.count or 0

    return render_template(
        "admin/dashboard.html",
        total_students=total_students,
        total_landlords=total_landlords,
        suspended_users=suspended_users,
        pending_kyc_count=pending_kyc_count,
        total_properties=total_properties,
        published_properties=published_properties,
        pending_reports_count=pending_reports_count
    )


@admin_bp.route("/landlords")
@login_required
@role_required("ADMIN")
def landlords():
    """Lists landlords with their verification and account statuses."""
    service = get_service_client()
    status_filter = request.args.get("status")

    query = service.table("landlord_verifications").select(
        "id, user_id, verification_status, identity_document_type, submitted_at, "
        "profiles:profiles!landlord_verifications_user_id_fkey(id, full_name, email, phone, account_status)"
    ).order("submitted_at", desc=True)

    if status_filter:
        query = query.eq("verification_status", status_filter)

    res = query.execute()
    return render_template("admin/landlords.html", verifications=res.data or [], current_filter=status_filter)


@admin_bp.route("/landlords/<verification_id>")
@login_required
@role_required("ADMIN")
def landlord_detail(verification_id: str):
    """Detailed KYC review view featuring temporary signed URL generation."""
    service = get_service_client()

    res = service.table("landlord_verifications").select(
        "*, profiles:profiles!landlord_verifications_user_id_fkey(id, full_name, email, phone, account_status, created_at)"
    ).eq("id", verification_id).execute()

    if not res.data:
        flash("Verification record not found.", "danger")
        return redirect(url_for("admin_bp.landlords"))

    verif = res.data[0]

    # Generate 15-minute temporary signed URL for private identity document
    signed_document_url = None
    if verif.get("identity_document_path"):
        signed_document_url = StorageService.generate_signed_url(
            bucket_name=Config.STORAGE_BUCKET_IDENTITY_DOCS,
            path=verif["identity_document_path"],
            expires_in_seconds=900
        )

    # Fetch properties already registered by this landlord
    props_res = service.table("properties").select("id, title, city, publishing_status").eq("owner_id", verif["user_id"]).execute()

    return render_template(
        "admin/landlord_detail.html",
        verif=verif,
        signed_document_url=signed_document_url,
        properties=props_res.data or []
    )

@admin_bp.route("/landlords/<verification_id>/action", methods=["POST"])
@login_required
@role_required("ADMIN")
def review_landlord(verification_id: str):
    """Processes approval, rejection, or info request on a landlord KYC record."""
    service = get_service_client()
    admin_id = session.get("user_id")

    decision = sanitize_string(request.form.get("decision"))
    review_note = sanitize_string(request.form.get("review_note"))

    if decision not in ("APPROVED", "REJECTED", "INFO_REQUIRED"):
        flash("Invalid KYC decision choice.", "warning")
        return redirect(url_for("admin_bp.landlord_detail", verification_id=verification_id))

    # Fetch existing verification
    verif_res = service.table("landlord_verifications").select("user_id").eq("id", verification_id).execute()
    if not verif_res.data:
        abort(404)

    target_user_id = verif_res.data[0]["user_id"]

    update_payload = {
        "verification_status": decision,
        "review_note": review_note,
        "reviewed_by": admin_id,
        "reviewed_at": "now()"
    }
    if decision == "REJECTED":
        update_payload["rejection_reason"] = review_note

    service.table("landlord_verifications").update(update_payload).eq("id", verification_id).execute()

    # If APPROVED, activate the user's account status
    if decision == "APPROVED":
        service.table("profiles").update({"account_status": "ACTIVE"}).eq("id", target_user_id).execute()

    # Dispatch notification to landlord
    notification_type = "VERIFICATION_APPROVED" if decision == "APPROVED" else "VERIFICATION_REJECTED"
    service.table("notifications").insert({
        "recipient_id": target_user_id,
        "title": f"Landlord Verification: {decision}",
        "message": f"Your verification request has been updated to {decision}. Note: {review_note or 'No remarks'}",
        "notification_type": notification_type,
        "action_url": "/landlord/dashboard"
    }).execute()

    # Audit log entry
    _record_audit_log(
        action=f"KYC_{decision}",
        entity_type="landlord_verification",
        entity_id=verification_id,
        metadata={"target_user_id": target_user_id, "review_note": review_note}
    )

    flash(f"Verification decision recorded: {decision}.", "success")
    return redirect(url_for("admin_bp.landlords"))


@admin_bp.route("/students")
@login_required
@role_required("ADMIN")
def students():
    """Lists registered student accounts."""
    service = get_service_client()
    res = service.table("profiles").select(
        "id, full_name, email, phone, account_status, created_at"
    ).eq("role", "STUDENT").order("created_at", desc=True).execute()

    return render_template("admin/students.html", students=res.data or [])


@admin_bp.route("/users/<user_id>/toggle-status", methods=["POST"])
@login_required
@role_required("ADMIN")
def toggle_user_status(user_id: str):
    """Toggles a user account between ACTIVE and SUSPENDED."""
    service = get_service_client()
    target_status = sanitize_string(request.form.get("status"))

    if target_status not in ("ACTIVE", "SUSPENDED"):
        flash("Invalid target account status.", "warning")
        return redirect(request.referrer or url_for("admin_bp.dashboard"))

    # Protect against self-suspension
    if user_id == session.get("user_id"):
        flash("Administrators cannot suspend their own accounts.", "danger")
        return redirect(request.referrer or url_for("admin_bp.dashboard"))

    service.table("profiles").update({"account_status": target_status}).eq("id", user_id).execute()

    _record_audit_log(
        action=f"USER_{target_status}",
        entity_type="profile",
        entity_id=user_id,
        metadata={"new_status": target_status}
    )

    flash(f"User account updated to {target_status}.", "success")
    return redirect(request.referrer or url_for("admin_bp.dashboard"))


@admin_bp.route("/properties")
@login_required
@role_required("ADMIN")
def properties():
    """Moderation queue for properties across the platform."""
    service = get_service_client()
    res = service.table("properties").select(
        "id, title, property_type, city, locality, publishing_status, created_at, "
        "owner:profiles!properties_owner_id_fkey(full_name, email)"
    ).order("created_at", desc=True).execute()

    return render_template("admin/properties.html", properties=res.data or [])


@admin_bp.route("/properties/<property_id>/status", methods=["POST"])
@login_required
@role_required("ADMIN")
def set_property_status(property_id: str):
    """Sets property publishing status (e.g. SUSPENDED or PUBLISHED)."""
    service = get_service_client()
    status = sanitize_string(request.form.get("status"))

    if status not in ("PUBLISHED", "UNPUBLISHED", "SUSPENDED"):
        flash("Invalid status choice.", "warning")
        return redirect(url_for("admin_bp.properties"))

    service.table("properties").update({"publishing_status": status}).eq("id", property_id).execute()

    _record_audit_log(
        action=f"PROPERTY_{status}",
        entity_type="property",
        entity_id=property_id,
        metadata={"status": status}
    )

    flash(f"Property status set to {status}.", "success")
    return redirect(url_for("admin_bp.properties"))


@admin_bp.route("/reports")
@login_required
@role_required("ADMIN")
def reports():
    """Moderation table for complaints filed against listings."""
    service = get_service_client()
    res = service.table("reports").select(
        "id, reason, description, status, created_at, "
        "reporter:profiles!reports_reporter_id_fkey(full_name, email), "
        "property:properties(id, title, city)"
    ).order("created_at", desc=True).execute()

    return render_template("admin/reports.html", reports=res.data or [])


@admin_bp.route("/reports/<report_id>/resolve", methods=["POST"])
@login_required
@role_required("ADMIN")
def resolve_report(report_id: str):
    """Marks a report as RESOLVED or DISMISSED with admin remarks."""
    service = get_service_client()
    decision = sanitize_string(request.form.get("decision"))
    resolution_notes = sanitize_string(request.form.get("resolution_notes"))

    if decision not in ("RESOLVED", "DISMISSED"):
        flash("Invalid resolution decision.", "warning")
        return redirect(url_for("admin_bp.reports"))

    service.table("reports").update({
        "status": decision,
        "resolution_notes": resolution_notes,
        "reviewed_by": session.get("user_id"),
        "reviewed_at": "now()"
    }).eq("id", report_id).execute()

    _record_audit_log(
        action=f"REPORT_{decision}",
        entity_type="report",
        entity_id=report_id,
        metadata={"decision": decision, "notes": resolution_notes}
    )

    flash(f"Report marked as {decision}.", "success")
    return redirect(url_for("admin_bp.reports"))


@admin_bp.route("/audit-logs")
@login_required
@role_required("ADMIN")
def audit_logs():
    """Displays chronological immutable security logs."""
    service = get_service_client()
    res = service.table("audit_logs").select(
        "id, action, entity_type, entity_id, metadata, ip_address, created_at, "
        "actor:profiles!audit_logs_actor_id_fkey(full_name, email)"
    ).order("created_at", desc=True).limit(100).execute()

    return render_template("admin/audit_logs.html", logs=res.data or [])