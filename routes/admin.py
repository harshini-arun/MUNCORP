"""
routes/admin.py
----------------
Administrator dashboard.

All admin modules are live: Citizens directory, Birth/Death Registrations,
License Applications, Hospital Certificate Codes, Sanitation Requests,
Tax Payments, and Grievances.

Each admin is assigned a citizen-ID range (zone_min..zone_max stored in the
Admin table). The dashboard displays this range and all sub-module views
filter data to only show records belonging to citizens in that range.
"""

from flask import Blueprint, render_template, session, url_for, flash, redirect
from mysql.connector import Error as MySQLError
from routes.auth import role_required
from routes.admin_utils import get_admin_zone
from database import get_db_connection

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _get_pending_counts(zone_min, zone_max):
    """
    Returns a dict of pending-item counts for each module, filtered to
    the admin's citizen-ID zone. Falls back to zeros on any DB error.
    """
    counts = {
        "birth": 0, "death": 0, "license": 0,
        "sanitation": 0, "grievance": 0,
    }
    if zone_min is None or zone_max is None:
        return counts
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM Birth_Registration "
            "WHERE Status='Pending' AND Parent_Citizen_ID BETWEEN %s AND %s",
            (zone_min, zone_max))
        counts["birth"] = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM Death_Registration "
            "WHERE Status='Pending' AND Citizen_ID BETWEEN %s AND %s",
            (zone_min, zone_max))
        counts["death"] = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM License "
            "WHERE Status='Pending' AND Citizen_ID BETWEEN %s AND %s",
            (zone_min, zone_max))
        counts["license"] = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM Sanitation_Request "
            "WHERE Status='Pending' AND Citizen_ID BETWEEN %s AND %s",
            (zone_min, zone_max))
        counts["sanitation"] = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM Grievance "
            "WHERE Status='Open' AND Citizen_ID BETWEEN %s AND %s",
            (zone_min, zone_max))
        counts["grievance"] = cur.fetchone()[0]

        cur.close()
        conn.close()
    except MySQLError:
        pass  # Return whatever we have; don't crash the dashboard
    return counts


def _modules(counts):
    """Built inside a request context so url_for() works."""
    return [
        {"name": "Citizens",                   "icon": "bi-people",
         "url": url_for("citizens_admin.list_citizens"),
         "badge": None},
        {"name": "Birth Registrations",        "icon": "bi-file-earmark-medical",
         "url": url_for("registration.admin_birth_registrations"),
         "badge": counts["birth"]},
        {"name": "Death Registrations",        "icon": "bi-file-earmark-text",
         "url": url_for("registration.admin_death_registrations"),
         "badge": counts["death"]},
        {"name": "License Applications",       "icon": "bi-card-checklist",
         "url": url_for("registration.admin_licenses"),
         "badge": counts["license"]},
        {"name": "Hospital Certificate Codes", "icon": "bi-hospital",
         "url": url_for("hospital.list_certificates"),
         "badge": None},
        {"name": "Sanitation Requests",        "icon": "bi-trash",
         "url": url_for("sanitation.admin_sanitation_requests"),
         "badge": counts["sanitation"]},
        {"name": "Tax Payments",               "icon": "bi-cash-coin",
         "url": url_for("tax.admin_tax_payments"),
         "badge": None},
        {"name": "Grievances",                 "icon": "bi-megaphone",
         "url": url_for("grievance.admin_grievances"),
         "badge": counts["grievance"]},
    ]


@admin_bp.route("/dashboard")
@role_required("admin")
def dashboard():
    zone_min = zone_max = None
    try:
        zone_min, zone_max = get_admin_zone(session["userId"])
    except (ValueError, MySQLError) as exc:
        flash(f"Warning: could not load your zone configuration. {exc}", "error")

    counts = _get_pending_counts(zone_min, zone_max)

    return render_template(
        "admin_dashboard.html",
        user_name=session.get("userName"),
        modules=_modules(counts),
        zone_min=zone_min,
        zone_max=zone_max,
    )


@admin_bp.route("/module/<module_name>")
@role_required("admin")
def module_placeholder(module_name):
    return render_template(
        "layout.html",
        title=module_name,
        content_message=f'"{module_name.replace("-", " ").title()}" module coming soon.',
        back_url="/admin/dashboard",
    )
