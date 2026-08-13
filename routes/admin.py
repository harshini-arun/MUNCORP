"""
routes/admin.py
----------------
Administrator dashboard.

Birth Registrations, Death Registrations, and License Applications are now
live (see routes/registration.py). Citizens, Tax Payments, Grievances, and
Sanitation Requests remain "Coming Soon" placeholders.
"""

from flask import Blueprint, render_template, session, url_for
from routes.auth import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _modules():
    """Built inside a request context so url_for() works."""
    return [
        {"name": "Citizens", "icon": "bi-people"},
        {"name": "Birth Registrations", "icon": "bi-file-earmark-medical",
         "url": url_for("registration.admin_birth_registrations")},
        {"name": "Death Registrations", "icon": "bi-file-earmark-text",
         "url": url_for("registration.admin_death_registrations")},
        {"name": "License Applications", "icon": "bi-card-checklist",
         "url": url_for("registration.admin_licenses")},
        {"name": "Hospital Certificate Codes", "icon": "bi-hospital",
         "url": url_for("hospital.list_certificates")},
        {"name": "Tax Payments", "icon": "bi-cash-coin"},
        {"name": "Grievances", "icon": "bi-megaphone"},
        {"name": "Sanitation Requests", "icon": "bi-trash"},
    ]


@admin_bp.route("/dashboard")
@role_required("admin")
def dashboard():
    return render_template(
        "admin_dashboard.html",
        user_name=session.get("userName"),
        modules=_modules(),
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
