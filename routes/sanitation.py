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
# Grouped by location (Area PIN), showing only pending request count.
# Priority ranked: locations with the most pending requests appear first.
# ====================================================================
@sanitation_bp.route("/admin/sanitation-requests", methods=["GET"])
@role_required("admin")
def admin_sanitation_requests():
    locations = []
    history = []
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT Area_PIN AS area_pin,
                   COUNT(*) AS pending_count,
                   MIN(Requested_Date) AS earliest_date
            FROM Sanitation_Request
            WHERE Status = 'Pending'
            GROUP BY Area_PIN
            ORDER BY pending_count DESC, earliest_date ASC
            """
        )
        locations = cursor.fetchall()

        cursor.execute(
            """
            SELECT Request_ID AS id, Area_PIN AS area_pin, Requested_Date AS requested_date,
                   Schedule_Date AS schedule_date, Status AS status
            FROM Sanitation_Request
            WHERE Status IN ('Scheduled', 'Rejected')
            ORDER BY COALESCE(Schedule_Date, Requested_Date) DESC, Request_ID DESC
            """
        )
        history = cursor.fetchall()

        cursor.close()
        connection.close()
    except MySQLError:
        flash("Could not load sanitation requests.", "error")
        locations = []
        history = []

    return render_template(
        "admin_sanitation_list.html",
        locations=locations,
        history=history,
        back_url=url_for("admin.dashboard"),
    )


@sanitation_bp.route("/admin/sanitation-requests/area/<area_pin>/schedule", methods=["POST"])
@role_required("admin")
def admin_schedule_sanitation_area(area_pin):
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
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE Sanitation_Request
            SET Status = 'Scheduled', Schedule_Date = %s
            WHERE Area_PIN = %s AND Status = 'Pending'
            """,
            (schedule_date, area_pin)
        )
        connection.commit()
        updated = cursor.rowcount
        cursor.close()
        connection.close()

        if updated > 0:
            flash(f"Scheduled {updated} request(s) for PIN code {area_pin} on {schedule_date}.", "success")
        else:
            flash(f"No pending requests found for PIN code {area_pin}.", "info")

    except MySQLError:
        flash("Could not schedule requests. Please try again later.", "error")

    return redirect(redirect_url)


@sanitation_bp.route("/admin/sanitation-requests/area/<area_pin>/reject", methods=["POST"])
@role_required("admin")
def admin_reject_sanitation_area(area_pin):
    redirect_url = url_for("sanitation.admin_sanitation_requests")

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE Sanitation_Request
            SET Status = 'Rejected'
            WHERE Area_PIN = %s AND Status = 'Pending'
            """,
            (area_pin,)
        )
        connection.commit()
        updated = cursor.rowcount
        cursor.close()
        connection.close()

        if updated > 0:
            flash(f"Rejected {updated} pending request(s) for PIN code {area_pin}.", "success")
        else:
            flash(f"No pending requests found for PIN code {area_pin}.", "info")

    except MySQLError:
        flash("Could not reject requests. Please try again later.", "error")

    return redirect(redirect_url)

