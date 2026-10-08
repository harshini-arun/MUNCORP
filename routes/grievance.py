"""
routes/grievance.py
--------------------
Public Grievance module.

Flow (ActivityDiagram.jpg):
    Raise Grievance
        -> Check for Approval Delay
        -> Delay Exists?  Yes -> Store Grievance -> Admin Response
                          No  -> Display Wait Message

So a grievance about a specific request is only accepted once that
request has actually been pending longer than the service window. If it
hasn't, the citizen is told to wait instead -- which is what stops the
queue filling up with complaints about requests filed an hour ago.

Delay checking needs a submission date, which is why
add_tax_and_grievance.sql adds Submitted_On to Birth/Death/License
(their existing date columns are event dates, not filing dates).
Sanitation already has Requested_Date.

A grievance not tied to any request ("General") skips the delay check --
there is no approval to be late.
"""

from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from mysql.connector import Error as MySQLError

from database import get_db_connection
from routes.auth import role_required
from routes.admin_utils import get_admin_zone

grievance_bp = Blueprint("grievance", __name__)

# How long a request may sit pending before a grievance is accepted.
SERVICE_WINDOW_DAYS = 7

CATEGORIES = [
    "Birth Registration",
    "Death Registration",
    "License",
    "Sanitation",
    "Tax",
    "Other",
]

# Reference_Type -> (table, pk column, owner column, submitted-date column)
REFERENCE_SOURCES = {
    "Birth":      ("Birth_Registration", "Birth_Reg_ID", "Parent_Citizen_ID", "Submitted_On"),
    "Death":      ("Death_Registration", "Death_Reg_ID", "Citizen_ID",        "Submitted_On"),
    "License":    ("License",            "License_ID",   "Citizen_ID",        "Submitted_On"),
    "Sanitation": ("Sanitation_Request", "Request_ID",   "Citizen_ID",        "Requested_Date"),
}


def _days_since(value):
    """Days between a DATE column and today. Tolerates date or string."""
    if value is None:
        return None
    if isinstance(value, date):
        submitted = value
    else:
        try:
            submitted = date.fromisoformat(str(value)[:10])
        except ValueError:
            return None
    return (date.today() - submitted).days


def check_approval_delay(cursor, reference_type, reference_id, citizen_id):
    """
    "Check for Approval Delay" from the activity diagram.

    Returns (delay_exists: bool, message: str or None). The message
    explains why a grievance was NOT accepted, when it wasn't.
    """
    source = REFERENCE_SOURCES.get(reference_type)
    if not source:
        return False, "Please choose a valid request type."

    table, pk_column, owner_column, date_column = source

    # Table/column names come from the fixed dictionary above, never
    # from user input, so they're safe to interpolate; values are still
    # passed as parameters.
    cursor.execute(
        f"SELECT {owner_column} AS owner_id, Status, {date_column} AS submitted_on "
        f"FROM {table} WHERE {pk_column} = %s",
        (reference_id,)
    )
    record = cursor.fetchone()

    if not record:
        return False, "We couldn't find a request with that ID."

    # A citizen may only raise a grievance about their own request.
    if record["owner_id"] != citizen_id:
        return False, "We couldn't find a request with that ID under your account."

    if record["Status"] != "Pending":
        return False, (f"That request has already been processed "
                       f"(status: {record['Status']}), so there's no approval delay to report.")

    days = _days_since(record["submitted_on"])
    if days is None:
        # No usable submission date -- don't block the citizen over a
        # data gap; let the grievance through for an admin to look at.
        return True, None

    if days < SERVICE_WINDOW_DAYS:
        remaining = SERVICE_WINDOW_DAYS - days
        return False, (f"That request was submitted {days} day(s) ago and is still within "
                       f"the {SERVICE_WINDOW_DAYS}-day processing window. "
                       f"Please wait {remaining} more day(s) before raising a grievance.")

    return True, None


# ====================================================================
# Citizen: raise a grievance
# ====================================================================
@grievance_bp.route("/grievance", methods=["GET", "POST"])
@role_required("citizen")
def raise_grievance():
    if request.method == "POST":
        # Category field was removed from the UI; derive it from reference_type.
        # Mapping must stay in sync with the CATEGORIES list above.
        _REFERENCE_TYPE_TO_CATEGORY = {
            "Birth":      "Birth Registration",
            "Death":      "Death Registration",
            "License":    "License",
            "Sanitation": "Sanitation",
            "General":    "Other",
            "":           "Other",
        }
        reference_type = request.form.get("reference_type", "").strip()
        category = _REFERENCE_TYPE_TO_CATEGORY.get(reference_type, "")
        description = request.form.get("description", "").strip()
        reference_id_raw = request.form.get("reference_id", "").strip()
        citizen_id = session["userId"]

        errors = []
        if category not in CATEGORIES:
            errors.append("Please choose a valid category.")
        if len(description) < 10:
            errors.append("Please describe the issue in at least 10 characters.")
        if len(description) > 2000:
            errors.append("Description is too long (max 2000 characters).")

        # "General" = not about a specific request.
        is_general = reference_type in ("", "General")
        reference_id = None
        if not is_general:
            if reference_type not in REFERENCE_SOURCES:
                errors.append("Please choose a valid request type.")
            elif not reference_id_raw.isdigit():
                errors.append("Please enter the numeric ID of the request you're complaining about.")
            else:
                reference_id = int(reference_id_raw)

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("grievance_form.html", categories=CATEGORIES)

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            if not is_general:
                delay_exists, message = check_approval_delay(
                    cursor, reference_type, reference_id, citizen_id)
                if not delay_exists:
                    # "Display Wait Message" branch -- nothing is stored.
                    flash(message, "error")
                    cursor.close()
                    connection.close()
                    return render_template("grievance_form.html", categories=CATEGORIES)

                # Don't let the same citizen file repeatedly about the
                # same request while the first one is still open.
                cursor.execute(
                    """
                    SELECT Grievance_ID FROM Grievance
                    WHERE Citizen_ID = %s AND Reference_Type = %s
                      AND Reference_ID = %s AND Status = 'Open'
                    """,
                    (citizen_id, reference_type, reference_id)
                )
                if cursor.fetchone():
                    flash("You already have an open grievance about that request.", "error")
                    cursor.close()
                    connection.close()
                    return render_template("grievance_form.html", categories=CATEGORIES)

            cursor.execute(
                """
                INSERT INTO Grievance
                    (Citizen_ID, Category, Description, Grievance_Date,
                     Reference_Type, Reference_ID, Status)
                VALUES (%s, %s, %s, %s, %s, %s, 'Open')
                """,
                (citizen_id, category, description, date.today(),
                 None if is_general else reference_type,
                 None if is_general else reference_id)
            )
            connection.commit()
            cursor.close()
            connection.close()

            flash("Grievance submitted successfully. Status: Open.", "success")
            return redirect(url_for("grievance.my_grievances"))

        except MySQLError:
            flash("Could not submit the grievance. Please try again later.", "error")
            return render_template("grievance_form.html", categories=CATEGORIES)

    return render_template("grievance_form.html", categories=CATEGORIES)


# ====================================================================
# Citizen: own grievances + admin responses (viewStatus())
# ====================================================================
@grievance_bp.route("/grievance/my", methods=["GET"])
@role_required("citizen")
def my_grievances():
    records = []
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT Grievance_ID, Category, Description, Grievance_Date,
                   Reference_Type, Reference_ID, Status, Admin_Response, Responded_On
            FROM Grievance
            WHERE Citizen_ID = %s
            ORDER BY FIELD(Status, 'Open', 'Resolved', 'Rejected'), Grievance_Date DESC
            """,
            (session["userId"],)
        )
        records = cursor.fetchall()
        cursor.close()
        connection.close()
    except MySQLError:
        flash("Could not load your grievances.", "error")

    return render_template("my_grievances.html", records=records)


# ====================================================================
# Admin: view + respond
# ====================================================================
@grievance_bp.route("/admin/grievances", methods=["GET"])
@role_required("admin")
def admin_grievances():
    zone_min = zone_max = None
    try:
        zone_min, zone_max = get_admin_zone(session["userId"])
    except (ValueError, MySQLError) as exc:
        flash(f"Could not load your zone: {exc}", "error")
        return redirect(url_for("admin.dashboard"))

    records = []
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT g.Grievance_ID, g.Citizen_ID, g.Category, g.Description,
                   g.Grievance_Date, g.Reference_Type, g.Reference_ID,
                   g.Status, g.Admin_Response, g.Responded_On,
                   c.name AS citizen_name
            FROM Grievance g
            LEFT JOIN Citizen c ON c.citizenId = g.Citizen_ID
            WHERE g.Citizen_ID BETWEEN %s AND %s
            ORDER BY FIELD(g.Status, 'Open', 'Resolved', 'Rejected'), g.Grievance_Date ASC
            """,
            (zone_min, zone_max)
        )
        records = cursor.fetchall()
        cursor.close()
        connection.close()
    except MySQLError:
        flash("Could not load grievances.", "error")

    return render_template(
        "admin_grievance_list.html",
        records=records,
        zone_min=zone_min,
        zone_max=zone_max,
        back_url=url_for("admin.dashboard"),
    )


@grievance_bp.route("/admin/grievances/<int:grievance_id>/respond", methods=["POST"])
@role_required("admin")
def admin_respond(grievance_id):
    response_text = request.form.get("response", "").strip()
    action = request.form.get("action", "").strip()
    redirect_url = url_for("grievance.admin_grievances")

    if action not in ("resolve", "reject"):
        flash("Invalid action.", "error")
        return redirect(redirect_url)
    if len(response_text) < 5:
        flash("Please write a response of at least 5 characters.", "error")
        return redirect(redirect_url)

    new_status = "Resolved" if action == "resolve" else "Rejected"

    try:
        zone_min, zone_max = get_admin_zone(session["userId"])
    except (ValueError, MySQLError) as exc:
        flash(f"Could not verify your zone: {exc}", "error")
        return redirect(redirect_url)

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT Citizen_ID, Status FROM Grievance WHERE Grievance_ID = %s",
            (grievance_id,)
        )
        record = cursor.fetchone()

        if not record:
            flash("Grievance not found.", "error")
        elif not (zone_min <= record["Citizen_ID"] <= zone_max):
            flash("That grievance is not in your assigned zone.", "error")
        elif record["Status"] != "Open":
            flash("This grievance has already been responded to.", "error")
        else:
            cursor.execute(
                """
                UPDATE Grievance
                SET Status = %s, Admin_Response = %s, Responded_On = %s
                WHERE Grievance_ID = %s
                """,
                (new_status, response_text, date.today(), grievance_id)
            )
            connection.commit()
            flash(f"Grievance #{grievance_id} marked as {new_status}.", "success")

        cursor.close()
        connection.close()

    except MySQLError:
        flash("Could not respond to the grievance. Please try again later.", "error")

    return redirect(redirect_url)

