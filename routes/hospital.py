"""
routes/hospital.py
-------------------
Manages the HospitalCertificate table from ClassDiagram.jpg:
    HospitalCertificate
    - hospitalName : String
    - medCertCode  : String (kept as VARCHAR to match Med_Cert_Code on
                     Birth_Registration / Death_Registration, so the two
                     can be compared directly)
    - issueDate    : Date

There's no separate "Hospital" actor in UseCase.jpg -- only Citizen and
Administrator -- so code management lives on the Admin side. Citizens
never see this table directly; they only find out whether their code
was accepted when they submit a Birth/Death Registration form.

verify_medical_cert_code() is the shared "verifyCode()" check used by
routes/registration.py before accepting a Birth or Death Registration.
"""

from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash
from mysql.connector import Error as MySQLError

from database import get_db_connection
from routes.auth import role_required

hospital_bp = Blueprint("hospital", __name__, url_prefix="/admin/hospital-certificates")


def verify_medical_cert_code(cursor, med_cert_code):
    """
    Shared verifyCode() logic for Birth/Death Registration.

    Returns a tuple (is_valid: bool, error_message: str or None).
    `cursor` must be an open dictionary cursor on an existing connection
    (the caller manages the connection/commit so the SELECT and the
    later INSERT + mark-as-used UPDATE happen on one connection).
    """
    cursor.execute(
        "SELECT Cert_ID, Used FROM HospitalCertificate WHERE Med_Cert_Code = %s",
        (med_cert_code,)
    )
    record = cursor.fetchone()

    if not record:
        return False, "This medical certificate code was not found. Please check the code with the issuing hospital."
    if record["Used"]:
        return False, "This medical certificate code has already been used for another registration."
    return True, None


def mark_cert_code_used(cursor, med_cert_code):
    """Marks a HospitalCertificate row as used. Caller commits."""
    cursor.execute(
        "UPDATE HospitalCertificate SET Used = 1 WHERE Med_Cert_Code = %s",
        (med_cert_code,)
    )


# ------------------------------------------------------------------
# Admin: view allotted codes + add new ones
# ------------------------------------------------------------------
@hospital_bp.route("", methods=["GET"])
@role_required("admin")
def list_certificates():
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT Cert_ID, Hospital_Name, Med_Cert_Code, Issue_Date, Used
            FROM HospitalCertificate
            ORDER BY Used ASC, Issue_Date DESC
            """
        )
        certificates = cursor.fetchall()
        cursor.close()
        connection.close()
    except MySQLError:
        flash("Could not load hospital certificate codes.", "error")
        certificates = []

    return render_template(
        "admin_hospital_certificates.html",
        certificates=certificates,
        back_url=url_for("admin.dashboard"),
    )


@hospital_bp.route("/add", methods=["POST"])
@role_required("admin")
def add_certificate():
    hospital_name = request.form.get("hospital_name", "").strip()
    med_cert_code = request.form.get("med_cert_code", "").strip()
    issue_date_raw = request.form.get("issue_date", "").strip()

    errors = []
    if not hospital_name:
        errors.append("Hospital name is required.")
    if not med_cert_code:
        errors.append("Medical certificate code is required.")

    from datetime import datetime
    issue_date = None
    try:
        issue_date = datetime.strptime(issue_date_raw, "%Y-%m-%d").date()
        if issue_date > date.today():
            errors.append("Issue date cannot be in the future.")
    except (ValueError, TypeError):
        errors.append("Please provide a valid issue date (YYYY-MM-DD).")

    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("hospital.list_certificates"))

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT Cert_ID FROM HospitalCertificate WHERE Med_Cert_Code = %s",
            (med_cert_code,)
        )
        if cursor.fetchone():
            flash("That medical certificate code has already been allotted.", "error")
            cursor.close()
            connection.close()
            return redirect(url_for("hospital.list_certificates"))

        cursor.execute(
            """
            INSERT INTO HospitalCertificate (Hospital_Name, Med_Cert_Code, Issue_Date, Used)
            VALUES (%s, %s, %s, 0)
            """,
            (hospital_name, med_cert_code, issue_date)
        )
        connection.commit()
        cursor.close()
        connection.close()

        flash(f"Code {med_cert_code} allotted to {hospital_name}.", "success")

    except MySQLError:
        flash("Could not add the certificate code. Please try again later.", "error")

    return redirect(url_for("hospital.list_certificates"))
