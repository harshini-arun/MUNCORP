"""
routes/citizen.py
------------------
Citizen dashboard (skeleton only).

The buttons on this dashboard correspond to future modules identified in
UseCase.jpg / ClassDiagram.jpg: Birth Registration, Death Registration,
License, Tax Payment, Sanitation Request, Grievance. Each currently routes
to a shared "Module Coming Soon" placeholder page.
"""

from flask import Blueprint, render_template, session
from routes.auth import role_required

citizen_bp = Blueprint("citizen", __name__, url_prefix="/citizen")

# Future modules, shown as cards on the dashboard (not yet implemented).
FUTURE_MODULES = [
    {"name": "Birth Registration", "icon": "bi-file-earmark-medical"},
    {"name": "Death Registration", "icon": "bi-file-earmark-text"},
    {"name": "Vehicle License", "icon": "bi-card-checklist"},
    {"name": "Tax Payment", "icon": "bi-cash-coin"},
    {"name": "Public Grievance", "icon": "bi-megaphone"},
    {"name": "Sanitation Request", "icon": "bi-trash"},
]


@citizen_bp.route("/dashboard")
@role_required("citizen")
def dashboard():
    return render_template(
        "citizen_dashboard.html",
        user_name=session.get("userName"),
        modules=FUTURE_MODULES,
    )


@citizen_bp.route("/module/<module_name>")
@role_required("citizen")
def module_placeholder(module_name):
    return render_template(
        "layout.html",
        title=module_name,
        content_message=f'"{module_name.replace("-", " ").title()}" module coming soon.',
        back_url="/citizen/dashboard",
    )
