"""
routes/landlord.py
Handles landlord dashboard, KYC submissions, property/room management, and inquiries.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from middleware.auth_guard import login_required
from middleware.role_guard import role_required, landlord_approved_required
from services.supabase_client import get_service_client
from services.storage_service import StorageService
from services.property_service import PropertyService
from services.room_service import RoomService
from utils.validators import sanitize_string, validate_coordinates, PINCODE_REGEX

landlord_bp = Blueprint("landlord_bp", __name__, url_prefix="/landlord")


@landlord_bp.route("/dashboard")
@login_required
@role_required("LANDLORD")
def dashboard():
    """Main landlord dashboard displaying status, inventory, and pending inquiries."""
    user_id = session.get("user_id")
    service = get_service_client()

    # Retrieve current verification status
    verif_res = service.table("landlord_verifications").select("*").eq("user_id", user_id).execute()
    verif_data = verif_res.data[0] if verif_res.data else {"verification_status": "UNSUBMITTED"}
    verification_status = verif_data.get("verification_status")

    # Counts
    props_res = service.table("properties").select("id", count="exact").eq("owner_id", user_id).execute()
    total_properties = props_res.count or 0

    # Rooms count
    rooms_res = service.table("rooms").select("id, availability_status, properties!inner(owner_id)").eq("properties.owner_id", user_id).execute()
    total_rooms = len(rooms_res.data) if rooms_res.data else 0
    available_rooms = sum(1 for r in (rooms_res.data or []) if r.get("availability_status") == "AVAILABLE")

    # Pending inquiries
    inq_res = service.table("inquiries").select("id", count="exact").eq("landlord_id", user_id).eq("status", "PENDING").execute()
    pending_inquiries = inq_res.count or 0

    return render_template(
        "landlord/dashboard.html",
        verification_status=verification_status,
        verif_data=verif_data,
        total_properties=total_properties,
        total_rooms=total_rooms,
        available_rooms=available_rooms,
        pending_inquiries=pending_inquiries
    )

@landlord_bp.route("/rooms/<room_id>/edit", methods=["GET", "POST"])
@login_required
@landlord_approved_required
def edit_room(room_id: str):
    """Room ki details, rent, policies aur amenities edit karna."""
    user_id = session.get("user_id")
    service = get_service_client()

    # Fetch room details along with amenities, images, and property check
    res = service.table("rooms").select(
        "*, amenities(*), room_images(*), properties!inner(id, title, owner_id)"
    ).eq("id", room_id).eq("properties.owner_id", user_id).execute()

    if not res.data:
        flash("Room nahi mila ya access denied hai.", "danger")
        return redirect(url_for("landlord_bp.properties"))

    room = res.data[0]
    amenities = room.get("amenities")
    if isinstance(amenities, list) and amenities:
        amenities = amenities[0]
    elif not isinstance(amenities, dict):
        amenities = {}

    if request.method == "POST":
        room_name = sanitize_string(request.form.get("room_name"))
        room_type = sanitize_string(request.form.get("room_type"))
        monthly_rent = float(request.form.get("monthly_rent", 0))
        security_deposit = float(request.form.get("security_deposit", 0))
        advance_rent = float(request.form.get("advance_rent", 0))
        cooler_charges = float(request.form.get("cooler_charges", 0))
        electricity_policy = sanitize_string(request.form.get("electricity_policy"))
        water_policy = sanitize_string(request.form.get("water_policy"))
        availability_status = sanitize_string(request.form.get("availability_status", "AVAILABLE"))

        if monthly_rent <= 0:
            flash("Monthly rent 0 se zyada honi chahiye.", "warning")
            return render_template("landlord/edit_room.html", room=room, amenities=amenities)

        room_data = {
            "room_name": room_name,
            "room_type": room_type,
            "monthly_rent": monthly_rent,
            "security_deposit": security_deposit,
            "advance_rent": advance_rent,
            "cooler_charges": cooler_charges,
            "electricity_policy": electricity_policy,
            "water_policy": water_policy,
            "availability_status": availability_status
        }

        amenities_data = {
            "has_wifi": request.form.get("has_wifi") == "on",
            "has_attached_bathroom": request.form.get("has_attached_bathroom") == "on",
            "has_ac": request.form.get("has_ac") == "on",
            "has_cooler": request.form.get("has_cooler") == "on",
            "has_bed": request.form.get("has_bed") == "on",
            "has_mattress": request.form.get("has_mattress") == "on",
            "has_study_table": request.form.get("has_study_table") == "on",
            "has_chair": request.form.get("has_chair") == "on",
            "has_cupboard": request.form.get("has_cupboard") == "on",
            "has_geyser": request.form.get("has_geyser") == "on",
            "has_ro_water": request.form.get("has_ro_water") == "on",
            "has_power_backup": request.form.get("has_power_backup") == "on",
            "has_cctv": request.form.get("has_cctv") == "on",
            "has_washing_machine": request.form.get("has_washing_machine") == "on"
        }

        success, msg = RoomService.update_room(room_id, user_id, room_data, amenities_data)

        # Nayi images upload handle karein agar select ki gayi hon
        new_files = request.files.getlist("new_room_images")
        prop_id = room.get("properties", {}).get("id")
        for f in new_files:
            if f and f.filename != "":
                s_ok, s_path = StorageService.upload_property_media(prop_id, f, f"rooms/{room_id}")
                if s_ok:
                    service.table("room_images").insert({
                        "room_id": room_id,
                        "storage_path": s_path,
                        "is_primary": False
                    }).execute()

        if success:
            flash("Room details update ho gayi hain!", "success")
            return redirect(url_for("landlord_bp.properties"))
        else:
            flash(f"Update failed: {msg}", "danger")

    return render_template("landlord/edit_room.html", room=room, amenities=amenities)


@landlord_bp.route("/rooms/<room_id>/delete", methods=["POST"])
@login_required
@landlord_approved_required
def delete_room(room_id: str):
    """Room ko permanently delete karna."""
    user_id = session.get("user_id")
    success, msg = RoomService.delete_room(room_id, user_id)
    flash(msg, "info" if success else "danger")
    return redirect(url_for("landlord_bp.properties"))


@landlord_bp.route("/rooms/images/<image_id>/delete", methods=["POST"])
@login_required
@landlord_approved_required
def delete_room_image(image_id: str):
    """Room ki specific photo delete karna."""
    user_id = session.get("user_id")
    room_id = request.form.get("room_id")
    success, msg = RoomService.delete_room_image(image_id, user_id)
    flash(msg, "info" if success else "danger")
    if room_id:
        return redirect(url_for("landlord_bp.edit_room", room_id=room_id))
    return redirect(url_for("landlord_bp.properties"))

@landlord_bp.route("/verification", methods=["GET", "POST"])
@login_required
@role_required("LANDLORD")
def verification_status():
    """Handles KYC document submissions."""
    user_id = session.get("user_id")
    service = get_service_client()

    if request.method == "POST":
        doc_type = sanitize_string(request.form.get("identity_document_type"))
        file = request.files.get("document_file")

        if not file or file.filename == "":
            flash("Please choose an identity/property ownership document to upload.", "warning")
            return redirect(url_for("landlord_bp.verification_status"))

        if doc_type not in ("ELECTRICITY_BILL", "PROPERTY_TAX_RECEIPT", "SALE_DEED", "RENT_AGREEMENT"):
            flash("Please choose a valid document category.", "warning")
            return redirect(url_for("landlord_bp.verification_status"))

        success, path_or_err = StorageService.upload_identity_document(user_id, file)
        if not success:
            flash(f"Upload failed: {path_or_err}", "danger")
            return redirect(url_for("landlord_bp.verification_status"))

        # Upsert record in landlord_verifications
        payload = {
            "user_id": user_id,
            "verification_status": "PENDING_REVIEW",
            "identity_document_type": doc_type,
            "identity_document_path": path_or_err,
            "submitted_at": "now()"
        }

        service.table("landlord_verifications").upsert(payload, on_conflict="user_id").execute()
        flash("Verification documents submitted successfully. Admin review is pending.", "success")
        return redirect(url_for("landlord_bp.verification_status"))

    verif_res = service.table("landlord_verifications").select("*").eq("user_id", user_id).execute()
    verif = verif_res.data[0] if verif_res.data else None

    return render_template("landlord/verification_status.html", verif=verif)


@landlord_bp.route("/properties")
@login_required
@landlord_approved_required
def properties():
    """Lists all properties owned by the verified landlord."""
    user_id = session.get("user_id")
    props = PropertyService.get_landlord_properties(user_id)
    return render_template("landlord/properties.html", properties=props)


@landlord_bp.route("/properties/add", methods=["GET", "POST"])
@login_required
@landlord_approved_required
def add_property():
    """Creates a new property and its initial rental policies."""
    user_id = session.get("user_id")

    if request.method == "POST":
        title = sanitize_string(request.form.get("title"))
        description = sanitize_string(request.form.get("description"))
        property_type = sanitize_string(request.form.get("property_type"))
        address_line = sanitize_string(request.form.get("address_line"))
        locality = sanitize_string(request.form.get("locality"))
        city = sanitize_string(request.form.get("city"))
        state = sanitize_string(request.form.get("state"))
        pincode = sanitize_string(request.form.get("pincode"))
        lat_raw = request.form.get("latitude")
        lon_raw = request.form.get("longitude")

        valid_coords, lat, lon = validate_coordinates(lat_raw, lon_raw)
        if not valid_coords:
            flash("Please supply valid GPS Latitude and Longitude coordinates.", "danger")
            return render_template("landlord/add_property.html", form=request.form)

        if not PINCODE_REGEX.match(pincode):
            flash("Pincode must be a valid 6-digit Indian PIN code.", "danger")
            return render_template("landlord/add_property.html", form=request.form)

        prop_data = {
            "title": title, "description": description, "property_type": property_type,
            "address_line": address_line, "locality": locality, "city": city,
            "state": state, "pincode": pincode, "latitude": lat, "longitude": lon
        }

        # Extract Rental Policies
        policies_data = {
            "is_24_hour_entry": request.form.get("is_24_hour_entry") == "on",
            "gate_closing_time": request.form.get("gate_closing_time") or None,
            "allows_day_guests": request.form.get("allows_day_guests") == "on",
            "allows_overnight_guests": request.form.get("allows_overnight_guests") == "on",
            "allows_self_cooking": request.form.get("allows_self_cooking") == "on",
            "allows_non_veg": request.form.get("allows_non_veg") == "on",
            "allows_smoking": request.form.get("allows_smoking") == "on",
            "allows_alcohol": request.form.get("allows_alcohol") == "on",
            "parking_available": request.form.get("parking_available") == "on",
            "two_wheeler_parking": request.form.get("two_wheeler_parking") == "on",
            "four_wheeler_parking": request.form.get("four_wheeler_parking") == "on",
            "notice_period_days": int(request.form.get("notice_period_days", 30)),
            "rent_due_day_of_month": int(request.form.get("rent_due_day_of_month", 5)),
            "custom_rules": sanitize_string(request.form.get("custom_rules"))
        }

        success, prop_id_or_err = PropertyService.create_property(user_id, prop_data, policies_data)
        if success:
            # Handle exterior/front property photos if uploaded
            files = request.files.getlist("property_images")
            for f in files:
                if f and f.filename != "":
                    s_ok, s_path = StorageService.upload_property_media(prop_id_or_err, f, "front")
                    if s_ok:
                        get_service_client().table("property_images").insert({
                            "property_id": prop_id_or_err,
                            "storage_path": s_path,
                            "image_type": "FRONT"
                        }).execute()

            flash("Property created successfully! You can now add rooms to this property.", "success")
            return redirect(url_for("landlord_bp.properties"))
        else:
            flash(f"Creation failed: {prop_id_or_err}", "danger")

    return render_template("landlord/add_property.html", form={})


@landlord_bp.route("/properties/<property_id>/rooms/add", methods=["GET", "POST"])
@login_required
@landlord_approved_required
def add_room(property_id: str):
    """Adds a room unit to a specific property."""
    user_id = session.get("user_id")
    property_obj = PropertyService.get_property_by_id(property_id, owner_id=user_id)
    if not property_obj:
        flash("Property not found or access denied.", "danger")
        return redirect(url_for("landlord_bp.properties"))

    if request.method == "POST":
        room_name = sanitize_string(request.form.get("room_name"))
        room_type = sanitize_string(request.form.get("room_type"))
        monthly_rent = float(request.form.get("monthly_rent", 0))
        security_deposit = float(request.form.get("security_deposit", 0))
        advance_rent = float(request.form.get("advance_rent", 0))
        cooler_charges = float(request.form.get("cooler_charges", 0))
        electricity_policy = sanitize_string(request.form.get("electricity_policy"))
        water_policy = sanitize_string(request.form.get("water_policy"))

        if monthly_rent <= 0:
            flash("Monthly rent must be a positive number.", "warning")
            return render_template("landlord/add_room.html", property=property_obj)

        room_data = {
            "room_name": room_name,
            "room_type": room_type,
            "monthly_rent": monthly_rent,
            "security_deposit": security_deposit,
            "advance_rent": advance_rent,
            "cooler_charges": cooler_charges,
            "electricity_policy": electricity_policy,
            "water_policy": water_policy,
            "availability_status": "AVAILABLE"
        }

        amenities_data = {
            "has_wifi": request.form.get("has_wifi") == "on",
            "has_attached_bathroom": request.form.get("has_attached_bathroom") == "on",
            "has_ac": request.form.get("has_ac") == "on",
            "has_cooler": request.form.get("has_cooler") == "on",
            "has_bed": request.form.get("has_bed") == "on",
            "has_mattress": request.form.get("has_mattress") == "on",
            "has_study_table": request.form.get("has_study_table") == "on",
            "has_chair": request.form.get("has_chair") == "on",
            "has_cupboard": request.form.get("has_cupboard") == "on",
            "has_geyser": request.form.get("has_geyser") == "on",
            "has_ro_water": request.form.get("has_ro_water") == "on",
            "has_power_backup": request.form.get("has_power_backup") == "on",
            "has_cctv": request.form.get("has_cctv") == "on",
            "has_washing_machine": request.form.get("has_washing_machine") == "on"
        }

        success, room_id_or_err = RoomService.add_room(property_id, user_id, room_data, amenities_data)
        if success:
            # Upload Room Photos
            files = request.files.getlist("room_images")
            for idx, f in enumerate(files):
                if f and f.filename != "":
                    s_ok, s_path = StorageService.upload_property_media(property_id, f, f"rooms/{room_id_or_err}")
                    if s_ok:
                        get_service_client().table("room_images").insert({
                            "room_id": room_id_or_err,
                            "storage_path": s_path,
                            "is_primary": idx == 0
                        }).execute()

            flash("Room added successfully to listing!", "success")
            return redirect(url_for("landlord_bp.properties"))
        else:
            flash(f"Error creating room: {room_id_or_err}", "danger")

    return render_template("landlord/add_room.html", property=property_obj)


@landlord_bp.route("/rooms/<room_id>/toggle-status", methods=["POST"])
@login_required
@landlord_approved_required
def toggle_room_status(room_id: str):
    """Toggles room status between AVAILABLE and OCCUPIED."""
    user_id = session.get("user_id")
    target_status = sanitize_string(request.form.get("status"))
    success, msg = RoomService.set_availability(room_id, user_id, target_status)
    flash(msg, "success" if success else "danger")
    return redirect(url_for("landlord_bp.properties"))


@landlord_bp.route("/inquiries")
@login_required
@landlord_approved_required
def inquiries():
    """Displays inquiries received from students across all properties."""
    user_id = session.get("user_id")
    service = get_service_client()

    res = service.table("inquiries").select(
        "id, message, move_in_date, status, landlord_response, created_at, "
        "rooms(id, room_name, monthly_rent), "
        "properties(id, title, locality, city), "
        "student:profiles!inquiries_student_id_fkey(full_name, email, phone)"
    ).eq("landlord_id", user_id).order("created_at", desc=True).execute()

    return render_template("landlord/inquiries.html", inquiries=res.data or [])


@landlord_bp.route("/inquiries/<inquiry_id>/respond", methods=["POST"])
@login_required
@landlord_approved_required
def respond_inquiry(inquiry_id: str):
    """Processes landlord decision (ACCEPT / REJECT) with an optional response note."""
    user_id = session.get("user_id")
    decision = sanitize_string(request.form.get("decision"))
    response_text = sanitize_string(request.form.get("response_text"))

    if decision not in ("ACCEPTED", "REJECTED"):
        flash("Invalid inquiry response.", "warning")
        return redirect(url_for("landlord_bp.inquiries"))

    service = get_service_client()
    try:
        inq_res = service.table("inquiries").update({
            "status": decision,
            "landlord_response": response_text
        }).eq("id", inquiry_id).eq("landlord_id", user_id).execute()

        if inq_res.data:
            student_id = inq_res.data[0]["student_id"]
            # Dispatch notification to student
            service.table("notifications").insert({
                "recipient_id": student_id,
                "title": f"Inquiry {decision.title()}",
                "message": f"The landlord has responded to your room inquiry: '{response_text}'",
                "notification_type": "INQUIRY_RESPONDED",
                "action_url": "/student/inquiries"
            }).execute()

            flash(f"Inquiry marked as {decision}.", "success")
        else:
            flash("Inquiry could not be updated.", "danger")
    except Exception as exc:
        flash(f"Error recording response: {exc}", "danger")

    return redirect(url_for("landlord_bp.inquiries"))