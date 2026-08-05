"""
routes/admin.py
----------------
Administrator dashboard (skeleton only).

Cards correspond to the Administrator's future responsibilities from
UseCase.jpg: approving/rejecting registrations, licenses, sanitation
requests, and responding to grievances. Not yet implemented.
"""

from flask import Blueprint, render_template, session
from routes.auth import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

FUTURE_MODULES = [
    {"name": "Birth Registrations", "icon": "bi-file-earmark-medical"},
    {"name": "Death Registrations", "icon": "bi-file-earmark-text"},
    {"name": "Licenses", "icon": "bi-card-checklist"},
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
        modules=FUTURE_MODULES,
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
