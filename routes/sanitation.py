"""
routes/sanitation.py
---------------------
Sanitation Request module (see ActivityDiagram.jpg / ClassDiagram.jpg /
UseCase.jpg):
    Citizen: Submit Request -> Rank by Duplicate Count Priority -> Store
    Admin:   Admin Scheduling -> Schedule/Reject -> Notify Citizen

Unlike Birth/Death/License (binary Approve/Reject), an admin here either
SCHEDULES a request (choosing a date) or REJECTS it -- so this has its
own small blueprint rather than reusing registration.py's generic
Approve/Reject helper.

Duplicate-count priority: multiple citizens often report the same
sanitation problem in the same area. Rather than storing a duplicate
count (which would go stale), it's computed live as "how many OTHER
pending requests share this Area PIN" and used to sort the admin's
queue -- areas with more complaints bubble to the top.

Any logged-in admin can view and act on any sanitation request (no
per-admin jurisdiction filtering here, same as Birth/Death/License).
"""

from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from mysql.connector import Error as MySQLError

from database import get_db_connection
from routes.auth import role_required
from routes.admin_utils import get_admin_zone

sanitation_bp = Blueprint("sanitation", __name__)

AREA_PIN_LENGTH = 6  # Indian PIN codes are 6 digits


def _required(value):
    return value is not None and str(value).strip() != ""


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


# ====================================================================
# Citizen: submit a sanitation request
# ====================================================================
@sanitation_bp.route("/sanitation-request", methods=["GET", "POST"])
@role_required("citizen")
def sanitation_request():
    if request.method == "POST":
        area_pin = request.form.get("area_pin", "").strip()
        citizen_id = session["userId"]

        errors = []
        if not _required(area_pin):
            errors.append("Area PIN is required.")
        elif not (area_pin.isdigit() and len(area_pin) == AREA_PIN_LENGTH):
            errors.append(f"Area PIN must be a {AREA_PIN_LENGTH}-digit PIN code.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("sanitation_request_form.html")

        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            # Don't let the same citizen queue up multiple pending
            # requests for the same area -- one active report is enough.
            cursor.execute(
                """
                SELECT Request_ID FROM Sanitation_Request
                WHERE Citizen_ID = %s AND Area_PIN = %s AND Status = 'Pending'
                """,
                (citizen_id, area_pin)
            )
            if cursor.fetchone():
                flash("You already have a pending sanitation request for this area.", "error")
                cursor.close()
                connection.close()
                return render_template("sanitation_request_form.html")

            cursor.execute(
                """
                INSERT INTO Sanitation_Request (Citizen_ID, Area_PIN, Requested_Date, Status)
                VALUES (%s, %s, %s, 'Pending')
                """,
                (citizen_id, area_pin, date.today())
            )
            connection.commit()
            cursor.close()
            connection.close()

            flash("Sanitation request submitted successfully. Status: Pending.", "success")
            return redirect(url_for("registration.my_registrations"))

        except MySQLError:
            flash("Could not save the request. Please try again later.", "error")
            return render_template("sanitation_request_form.html")

    return render_template("sanitation_request_form.html")


# ====================================================================
# Admin: view + schedule/reject requests
# ====================================================================
@sanitation_bp.route("/admin/sanitation-requests", methods=["GET"])
@role_required("admin")
def admin_sanitation_requests():
    zone_min = zone_max = None
    try:
        zone_min, zone_max = get_admin_zone(session["userId"])
    except (ValueError, MySQLError) as exc:
        flash(f"Could not load your zone: {exc}", "error")
        return redirect(url_for("admin.dashboard"))

    rows = []
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT s.Request_ID, s.Citizen_ID, s.Area_PIN, s.Requested_Date,
                   s.Schedule_Date, s.Status, c.name AS citizen_name,
                   (SELECT COUNT(*) FROM Sanitation_Request s2
                    WHERE s2.Area_PIN = s.Area_PIN AND s2.Status = 'Pending') AS duplicate_count
            FROM Sanitation_Request s
            LEFT JOIN Citizen c ON c.citizenId = s.Citizen_ID
            WHERE s.Citizen_ID BETWEEN %s AND %s
            ORDER BY FIELD(s.Status, 'Pending', 'Scheduled', 'Rejected'),
                     duplicate_count DESC, s.Requested_Date ASC
            """,
            (zone_min, zone_max)
        )
        records = cursor.fetchall()
        cursor.close()
        connection.close()

        rows = [{
            "id": r["Request_ID"],
            "status": r["Status"],
            "citizen_name": r["citizen_name"] or "Unknown",
            "citizen_id": r["Citizen_ID"],
            "area_pin": r["Area_PIN"],
            "requested_date": r["Requested_Date"],
            "schedule_date": r["Schedule_Date"],
            "duplicate_count": r["duplicate_count"],
        } for r in records]

    except MySQLError:
        flash("Could not load sanitation requests.", "error")
        rows = []

    return render_template(
        "admin_sanitation_list.html",
        rows=rows,
        zone_min=zone_min,
        zone_max=zone_max,
        back_url=url_for("admin.dashboard"),
    )


@sanitation_bp.route("/admin/sanitation-requests/<int:request_id>/schedule", methods=["POST"])
@role_required("admin")
def admin_schedule_sanitation(request_id):
    schedule_date_raw = request.form.get("schedule_date", "").strip()
    schedule_date = _parse_date(schedule_date_raw)
    redirect_url = url_for("sanitation.admin_sanitation_requests")

    if not schedule_date:
        flash("Please provide a valid schedule date.", "error")
        return redirect(redirect_url)
    if schedule_date < date.today():
        flash("Schedule date cannot be in the past.", "error")
        return redirect(redirect_url)

    try:
        zone_min, zone_max = get_admin_zone(session["userId"])
    except (ValueError, MySQLError) as exc:
        flash(f"Could not verify your zone: {exc}", "error")
        return redirect(redirect_url)

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT Citizen_ID, Status FROM Sanitation_Request WHERE Request_ID = %s",
            (request_id,)
        )
        record = cursor.fetchone()

        if not record:
            flash("Request not found.", "error")
        elif not (zone_min <= record["Citizen_ID"] <= zone_max):
            flash("That request is not in your assigned zone.", "error")
        elif record["Status"] != "Pending":
            flash("This request has already been handled.", "error")
        else:
            cursor.execute(
                """
                UPDATE Sanitation_Request
                SET Status = 'Scheduled', Schedule_Date = %s
                WHERE Request_ID = %s
                """,
                (schedule_date, request_id)
            )
            connection.commit()
            flash(f"Request #{request_id} scheduled for {schedule_date}.", "success")

        cursor.close()
        connection.close()

    except MySQLError:
        flash("Could not schedule the request. Please try again later.", "error")

    return redirect(redirect_url)


@sanitation_bp.route("/admin/sanitation-requests/<int:request_id>/reject", methods=["POST"])
@role_required("admin")
def admin_reject_sanitation(request_id):
    redirect_url = url_for("sanitation.admin_sanitation_requests")

    try:
        zone_min, zone_max = get_admin_zone(session["userId"])
    except (ValueError, MySQLError) as exc:
        flash(f"Could not verify your zone: {exc}", "error")
        return redirect(redirect_url)

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT Citizen_ID, Status FROM Sanitation_Request WHERE Request_ID = %s",
            (request_id,)
        )
        record = cursor.fetchone()

        if not record:
            flash("Request not found.", "error")
        elif not (zone_min <= record["Citizen_ID"] <= zone_max):
            flash("That request is not in your assigned zone.", "error")
        elif record["Status"] != "Pending":
            flash("This request has already been handled.", "error")
        else:
            cursor.execute(
                "UPDATE Sanitation_Request SET Status = 'Rejected' WHERE Request_ID = %s",
                (request_id,)
            )
            connection.commit()
            flash(f"Request #{request_id} rejected.", "success")

        cursor.close()
        connection.close()

    except MySQLError:
        flash("Could not reject the request. Please try again later.", "error")

    return redirect(redirect_url)

