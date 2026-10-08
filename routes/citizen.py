"""
routes/citizen.py
------------------
Citizen dashboard.

Birth Registration, Death Registration, and License Registration are now
live (see routes/registration.py). Tax Payment, Public Grievance, and
Sanitation Request remain "Coming Soon" placeholders.
"""

from flask import Blueprint, render_template, session, url_for
from routes.auth import role_required

citizen_bp = Blueprint("citizen", __name__, url_prefix="/citizen")


def _modules():
    """Built inside a request context so url_for() works."""
    return [
        {"name": "Birth Registration", "icon": "bi-file-earmark-medical",
         "url": url_for("registration.birth_registration")},
        {"name": "Death Registration", "icon": "bi-file-earmark-text",
         "url": url_for("registration.death_registration")},
        {"name": "License Registration", "icon": "bi-card-checklist",
         "url": url_for("registration.license_registration")},
        {"name": "Tax Payment", "icon": "bi-cash-coin",
         "url": url_for("tax.tax_payment")},
        {"name": "Public Grievance", "icon": "bi-megaphone",
         "url": url_for("grievance.raise_grievance")},
        {"name": "Sanitation Request", "icon": "bi-trash",
        "url": url_for("sanitation.sanitation_request")},
    ]


@citizen_bp.route("/dashboard")
@role_required("citizen")
def dashboard():
    return render_template(
        "citizen_dashboard.html",
        user_name=session.get("userName"),
        modules=_modules(),
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
