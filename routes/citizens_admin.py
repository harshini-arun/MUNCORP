"""
routes/citizens_admin.py
-------------------------
Admin-side Citizens directory ("Citizens" card on the admin dashboard).

Two views:
    /admin/citizens             list citizens IN THIS ADMIN'S zone + activity counts
    /admin/citizens/<id>        one citizen's full record across modules

Admin zone filtering
--------------------
Each admin is assigned a citizen-ID range (zone_min..zone_max). All queries
here are restricted to that range, preventing admins from viewing citizens
belonging to another admin's zone. Direct URL access (e.g. /admin/citizens/2001
by Admin 1) is also blocked by checking the citizen ID against the zone.

Passwords, password hashes, and OTP columns are never selected here --
an admin has no business seeing them, so they don't leave the database.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from mysql.connector import Error as MySQLError

from database import get_db_connection
from routes.auth import role_required
from routes.admin_utils import get_admin_zone

citizens_admin_bp = Blueprint("citizens_admin", __name__, url_prefix="/admin/citizens")


def _load_zone():
    """
    Returns (zone_min, zone_max) for the currently logged-in admin.
    Flashes an error and returns (None, None) on failure.
    """
    try:
        return get_admin_zone(session["userId"])
    except (ValueError, MySQLError) as exc:
        flash(f"Could not load your admin zone: {exc}", "error")
        return None, None


@citizens_admin_bp.route("", methods=["GET"])
@role_required("admin")
def list_citizens():
    search = request.args.get("q", "").strip()
    citizens = []

    zone_min, zone_max = _load_zone()
    if zone_min is None:
        return redirect(url_for("admin.dashboard"))

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # NOTE: password is never selected.
        # (c.password IS NOT NULL AND c.password != '') is a safe way to show
        # whether the account row is populated, without leaking the hash.
        base_query = """
            SELECT c.citizenId, c.name, c.phone, c.email,
                   (c.password IS NOT NULL AND c.password != '') AS password_set,
                   (SELECT COUNT(*) FROM Birth_Registration b
                    WHERE b.Parent_Citizen_ID = c.citizenId) AS birth_count,
                   (SELECT COUNT(*) FROM Death_Registration d
                    WHERE d.Citizen_ID = c.citizenId) AS death_count,
                   (SELECT COUNT(*) FROM License l
                    WHERE l.Citizen_ID = c.citizenId) AS license_count,
                   (SELECT COUNT(*) FROM Sanitation_Request s
                    WHERE s.Citizen_ID = c.citizenId) AS sanitation_count,
                   (SELECT COUNT(*) FROM Tax_Payment t
                    WHERE t.Citizen_ID = c.citizenId) AS tax_count,
                   (SELECT COUNT(*) FROM Grievance g
                    WHERE g.Citizen_ID = c.citizenId AND g.Status = 'Open') AS open_grievances
            FROM Citizen c
            WHERE c.citizenId BETWEEN %s AND %s
        """

        if search:
            like = f"%{search}%"
            cursor.execute(
                base_query
                + " AND (c.name LIKE %s OR CAST(c.citizenId AS CHAR) = %s)"
                  " ORDER BY c.citizenId",
                (zone_min, zone_max, like, search)
            )
        else:
            cursor.execute(base_query + " ORDER BY c.citizenId", (zone_min, zone_max))

        citizens = cursor.fetchall()
        cursor.close()
        connection.close()

    except MySQLError:
        flash("Could not load the citizen directory.", "error")

    return render_template(
        "admin_citizens_list.html",
        citizens=citizens,
        search=search,
        zone_min=zone_min,
        zone_max=zone_max,
        back_url=url_for("admin.dashboard"),
    )


@citizens_admin_bp.route("/<int:citizen_id>", methods=["GET"])
@role_required("admin")
def citizen_detail(citizen_id):
    zone_min, zone_max = _load_zone()
    if zone_min is None:
        return redirect(url_for("admin.dashboard"))

    # Prevent URL bypass: block access to citizens outside this admin's zone.
    if not (zone_min <= citizen_id <= zone_max):
        flash("That citizen is not in your assigned zone.", "error")
        return redirect(url_for("citizens_admin.list_citizens"))

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT citizenId, name, phone, email,
                   (password IS NOT NULL AND password != '') AS password_set
            FROM Citizen WHERE citizenId = %s
            """,
            (citizen_id,)
        )
        citizen = cursor.fetchone()

        if not citizen:
            cursor.close()
            connection.close()
            flash("Citizen not found.", "error")
            return redirect(url_for("citizens_admin.list_citizens"))

        cursor.execute(
            """
            SELECT Birth_Reg_ID AS id, Child_Name AS detail, Birth_Date AS record_date, Status
            FROM Birth_Registration WHERE Parent_Citizen_ID = %s ORDER BY Birth_Reg_ID DESC
            """, (citizen_id,))
        births = cursor.fetchall()

        cursor.execute(
            """
            SELECT Death_Reg_ID AS id, Name AS detail, Death_Date AS record_date, Status
            FROM Death_Registration WHERE Citizen_ID = %s ORDER BY Death_Reg_ID DESC
            """, (citizen_id,))
        deaths = cursor.fetchall()

        cursor.execute(
            """
            SELECT License_ID AS id, Vehicle_ID AS detail, Renewal_Date AS record_date, Status
            FROM License WHERE Citizen_ID = %s ORDER BY License_ID DESC
            """, (citizen_id,))
        licenses = cursor.fetchall()

        cursor.execute(
            """
            SELECT Request_ID AS id, Area_PIN AS detail, Requested_Date AS record_date, Status
            FROM Sanitation_Request WHERE Citizen_ID = %s ORDER BY Request_ID DESC
            """, (citizen_id,))
        sanitation = cursor.fetchall()

        cursor.execute(
            """
            SELECT Transaction_ID AS id, Tax_Type AS detail, Payment_Date AS record_date,
                   Tax_Amount
            FROM Tax_Payment WHERE Citizen_ID = %s ORDER BY Transaction_ID DESC
            """, (citizen_id,))
        taxes = cursor.fetchall()

        cursor.execute(
            """
            SELECT Grievance_ID AS id, Category AS detail, Grievance_Date AS record_date, Status
            FROM Grievance WHERE Citizen_ID = %s ORDER BY Grievance_ID DESC
            """, (citizen_id,))
        grievances = cursor.fetchall()

        cursor.close()
        connection.close()

    except MySQLError:
        flash("Could not load that citizen's record.", "error")
        return redirect(url_for("citizens_admin.list_citizens"))

    sections = [
        ("Birth Registrations",  "bi-file-earmark-medical", births,    "Child Name"),
        ("Death Registrations",  "bi-file-earmark-text",    deaths,    "Name"),
        ("License Applications", "bi-card-checklist",       licenses,  "Vehicle ID"),
        ("Sanitation Requests",  "bi-trash",                sanitation, "Area PIN"),
        ("Grievances",           "bi-megaphone",            grievances, "Category"),
    ]

    return render_template(
        "admin_citizen_detail.html",
        citizen=citizen,
        sections=sections,
        taxes=taxes,
        zone_min=zone_min,
        zone_max=zone_max,
        back_url=url_for("citizens_admin.list_citizens"),
    )
