"""
app.py
------
Main entry point for the Municipal Corporation Management System (Phase 1).

Phase 1 scope ONLY:
    - Login
    - Authentication
    - Session management
    - Logout
    - Role-based dashboard redirection (Citizen / Administrator)

Future modules (Birth/Death Registration, License, Tax, Grievance,
Sanitation, etc. -- see ClassDiagram.jpg / UseCase.jpg) are represented
only as placeholder links on the dashboards and are NOT implemented yet.
"""

from flask import Flask, render_template, session, redirect, url_for
from config import SECRET_KEY

# Blueprints
from routes.auth import auth_bp
from routes.citizen import citizen_bp
from routes.admin import admin_bp
from routes.registration import registration_bp
from routes.hospital import hospital_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(citizen_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(registration_bp)
    app.register_blueprint(hospital_bp)

    @app.route("/")
    def index():
        """
        Root route: send logged-in users to their dashboard,
        everyone else to the login page.
        """
        if "userId" in session:
            if session.get("role") == "citizen":
                return redirect(url_for("citizen.dashboard"))
            elif session.get("role") == "admin":
                return redirect(url_for("admin.dashboard"))
        return redirect(url_for("auth.login"))

    @app.errorhandler(404)
    def not_found(e):
        return render_template("layout.html", title="Not Found",
                                content_message="Page not found."), 404

    return app


if __name__ == "__main__":
    app = create_app()
    # debug=True is fine for local development; turn off in production.
    app.run(debug=True)
