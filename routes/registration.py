"""
routes/registration.py
-----------------------
Implements THREE modules on top of the existing auth system:
    1. Birth Registration
    2. Death Registration
    3. License Registration

Design notes
------------
- This file does NOT touch login/logout/session code in routes/auth.py.
  It only imports the existing `role_required` decorator from there.
- The logged-in citizen's ID (session["userId"]) is always used as the
  owner of a new record -- it is never taken from form input -- so a
  citizen can never submit (or later view) a registration under someone
  else's Citizen ID. This also means citizens can't tamper with the
  "Parent Citizen ID" / "Citizen ID" field to impersonate another user.
- Admin approve/reject actions run an UPDATE ... WHERE id = %s with the
  new status, using parameterized queries throughout.
- All three tables use Status ENUM('Pending','Approved','Rejected').
"""

from datetime import datetime, date

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from mysql.connector import Error as MySQLError

from database import get_db_connection
from routes.auth import role_required
from routes.hospital import verify_medical_cert_code, mark_cert_code_used
from routes.admin_utils import get_admin_zone

registration_bp = Blueprint("registration", __name__)


# ------------------------------------------------------------------
# Small shared validation helpers
# ------------------------------------------------------------------
def _required(value):
    return value is not None and str(value).strip() != ""


def _parse_date(value):
    """Returns a date object if value is a valid YYYY-MM-DD date, else None."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _parse_time(value):
    """Returns a normalized HH:MM:SS string if value is a valid HH:MM time, else None."""
    try:
        return datetime.strptime(value, "%H:%M").strftime("%H:%M:00")
    except (ValueError, TypeError):
        return None


def _citizen_exists(cursor, citizen_id):
    """Checks the Citizen table for a given citizenId. cursor can be dict or plain."""
    cursor.execute("SELECT citizenId FROM Citizen WHERE citizenId = %s", (citizen_id,))
    return cursor.fetchone() is not None


# ====================================================================
# 1. BIRTH REGISTRATION
# ====================================================================
@registration_bp.route("/birth-registration", methods=["GET", "POST"])
@role_required("citizen")
def birth_registration():
    if request.method == "POST":
        child_name = request.form.get("child_name", "").strip()
        parent_name = request.form.get("parent_name", "").strip()
        parent_citizen_id_raw = request.form.get("parent_citizen_id", "").strip()
        place_of_birth = request.form.get("place_of_birth", "").strip()
        birth_date_raw = request.form.get("birth_date", "").strip()
        birth_time_raw = request.form.get("birth_time", "").strip()
        med_cert_code = request.form.get("med_cert_code", "").strip()

        errors = []
        if not _required(child_name):
            errors.append("Child name is required.")
        if not _required(parent_name):
            errors.append("Parent name is required.")
        if not _required(place_of_birth):
            errors.append("Place of birth is required.")
        if not _required(med_cert_code):
            errors.append("Medical certificate code is required.")

        if not parent_citizen_id_raw.isdigit():
            errors.append("Parent Citizen ID must be a valid numeric Citizen ID.")
            parent_citizen_id = None
        else:
            parent_citizen_id = int(parent_citizen_id_raw)

        birth_date = _parse_date(birth_date_raw)
        if not birth_date:
            errors.append("Please provide a valid birth date (YYYY-MM-DD).")
        elif birth_date > date.today():
            errors.append("Birth date cannot be in the future.")

        birth_time = _parse_time(birth_time_raw)
        if not birth_time:
            errors.append("Please provide a valid birth time (HH:MM).")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("birth_registration_form.html")

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            # The Parent Citizen ID is user-editable, so make sure it
            # actually refers to a real citizen before inserting --
            # otherwise the foreign key would just reject it with a
            # generic database error.
            if not _citizen_exists(cursor, parent_citizen_id):
                flash("No citizen was found with that Parent Citizen ID.", "error")
                cursor.close()
                connection.close()
                return render_template("birth_registration_form.html")

            # verifyCode() -- confirm the medical certificate code was
            # actually issued by a hospital and hasn't been used already.
            is_valid, error_message = verify_medical_cert_code(cursor, med_cert_code)
            if not is_valid:
                flash(error_message, "error")
                cursor.close()
                connection.close()
                return render_template("birth_registration_form.html")

            cursor.execute(
                """
                INSERT INTO Birth_Registration
                    (Child_Name, Parent_Name, Parent_Citizen_ID, Place_of_Birth,
                     Birth_Date, Birth_Time, Med_Cert_Code, Status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pending')
                """,
                (child_name, parent_name, parent_citizen_id, place_of_birth,
                 birth_date, birth_time, med_cert_code)
            )
            mark_cert_code_used(cursor, med_cert_code)
            connection.commit()
            cursor.close()
            connection.close()

            flash("Birth registration submitted successfully. Status: Pending.", "success")
            return redirect(url_for("registration.my_registrations"))

        except MySQLError:
            flash("Could not save the registration. Please try again later.", "error")
            return render_template("birth_registration_form.html")

    return render_template("birth_registration_form.html")


@registration_bp.route("/admin/birth-registrations", methods=["GET"])
@role_required("admin")
def admin_birth_registrations():
    zone_min = zone_max = None
    try:
        zone_min, zone_max = get_admin_zone(session["userId"])
    except (ValueError, MySQLError) as exc:
        flash(f"Could not load your zone: {exc}", "error")
        return redirect(url_for("admin.dashboard"))

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT b.Birth_Reg_ID, b.Child_Name, b.Parent_Name, b.Parent_Citizen_ID,
                   b.Place_of_Birth, b.Birth_Date, b.Birth_Time, b.Med_Cert_Code, b.Status,
                   c.name AS citizen_name
            FROM Birth_Registration b
            LEFT JOIN Citizen c ON c.citizenId = b.Parent_Citizen_ID
            WHERE b.Parent_Citizen_ID BETWEEN %s AND %s
            ORDER BY FIELD(b.Status, 'Pending', 'Approved', 'Rejected'), b.Birth_Date DESC
            """,
            (zone_min, zone_max)
        )
        records = cursor.fetchall()
        cursor.close()
        connection.close()
    except MySQLError:
        flash("Could not load birth registrations.", "error")
        records = []

    rows = [{
        "id": r["Birth_Reg_ID"],
        "status": r["Status"],
        "citizen_name": r["citizen_name"] or "Unknown",
        "citizen_id": r["Parent_Citizen_ID"],
        "fields": [
            ("Child Name", r["Child_Name"]),
            ("Parent Name", r["Parent_Name"]),
            ("Place of Birth", r["Place_of_Birth"]),
            ("Birth Date", r["Birth_Date"]),
            ("Birth Time", r["Birth_Time"]),
            ("Medical Cert. Code", r["Med_Cert_Code"]),
        ],
    } for r in records]

    return render_template(
        "admin_registration_list.html",
        title="Birth Registrations",
        rows=rows,
        approve_endpoint="registration.admin_birth_action",
        zone_min=zone_min,
        zone_max=zone_max,
        back_url=url_for("admin.dashboard"),
    )


@registration_bp.route("/admin/birth-registrations/<int:reg_id>/<action>", methods=["POST"])
@role_required("admin")
def admin_birth_action(reg_id, action):
    return _update_status("Birth_Registration", "Birth_Reg_ID", reg_id, action,
                           url_for("registration.admin_birth_registrations"),
                           citizen_col="Parent_Citizen_ID")


# ====================================================================
# 2. DEATH REGISTRATION
# ====================================================================
@registration_bp.route("/death-registration", methods=["GET", "POST"])
@role_required("citizen")
def death_registration():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        place_of_death = request.form.get("place_of_death", "").strip()
        death_date_raw = request.form.get("death_date", "").strip()
        death_time_raw = request.form.get("death_time", "").strip()
        med_cert_code = request.form.get("med_cert_code", "").strip()

        # Logged-in citizen is automatically the person filing the record.
        citizen_id = session["userId"]

        errors = []
        if not _required(name):
            errors.append("Name is required.")
        if not _required(place_of_death):
            errors.append("Place of death is required.")
        if not _required(med_cert_code):
            errors.append("Medical certificate code is required.")

        death_date = _parse_date(death_date_raw)
        if not death_date:
            errors.append("Please provide a valid death date (YYYY-MM-DD).")
        elif death_date > date.today():
            errors.append("Death date cannot be in the future.")

        death_time = _parse_time(death_time_raw)
        if not death_time:
            errors.append("Please provide a valid death time (HH:MM).")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("death_registration_form.html")

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            is_valid, error_message = verify_medical_cert_code(cursor, med_cert_code)
            if not is_valid:
                flash(error_message, "error")
                cursor.close()
                connection.close()
                return render_template("death_registration_form.html")

            cursor.execute(
                """
                INSERT INTO Death_Registration
                    (Name, Citizen_ID, Place_of_Death, Death_Date, Death_Time, Med_Cert_Code, Status)
                VALUES (%s, %s, %s, %s, %s, %s, 'Pending')
                """,
                (name, citizen_id, place_of_death, death_date, death_time, med_cert_code)
            )
            mark_cert_code_used(cursor, med_cert_code)
            connection.commit()
            cursor.close()
            connection.close()

            flash("Death registration submitted successfully. Status: Pending.", "success")
            return redirect(url_for("registration.my_registrations"))

        except MySQLError:
            flash("Could not save the registration. Please try again later.", "error")
            return render_template("death_registration_form.html")

    return render_template("death_registration_form.html")


@registration_bp.route("/admin/death-registrations", methods=["GET"])
@role_required("admin")
def admin_death_registrations():
    zone_min = zone_max = None
    try:
        zone_min, zone_max = get_admin_zone(session["userId"])
    except (ValueError, MySQLError) as exc:
        flash(f"Could not load your zone: {exc}", "error")
        return redirect(url_for("admin.dashboard"))

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT d.Death_Reg_ID, d.Name, d.Citizen_ID, d.Place_of_Death,
                   d.Death_Date, d.Death_Time, d.Med_Cert_Code, d.Status,
                   c.name AS citizen_name
            FROM Death_Registration d
            LEFT JOIN Citizen c ON c.citizenId = d.Citizen_ID
            WHERE d.Citizen_ID BETWEEN %s AND %s
            ORDER BY FIELD(d.Status, 'Pending', 'Approved', 'Rejected'), d.Death_Date DESC
            """,
            (zone_min, zone_max)
        )
        records = cursor.fetchall()
        cursor.close()
        connection.close()
    except MySQLError:
        flash("Could not load death registrations.", "error")
        records = []

    rows = [{
        "id": r["Death_Reg_ID"],
        "status": r["Status"],
        "citizen_name": r["citizen_name"] or "Unknown",
        "citizen_id": r["Citizen_ID"],
        "fields": [
            ("Name", r["Name"]),
            ("Place of Death", r["Place_of_Death"]),
            ("Death Date", r["Death_Date"]),
            ("Death Time", r["Death_Time"]),
            ("Medical Cert. Code", r["Med_Cert_Code"]),
        ],
    } for r in records]

    return render_template(
        "admin_registration_list.html",
        title="Death Registrations",
        rows=rows,
        approve_endpoint="registration.admin_death_action",
        zone_min=zone_min,
        zone_max=zone_max,
        back_url=url_for("admin.dashboard"),
    )


@registration_bp.route("/admin/death-registrations/<int:reg_id>/<action>", methods=["POST"])
@role_required("admin")
def admin_death_action(reg_id, action):
    return _update_status("Death_Registration", "Death_Reg_ID", reg_id, action,
                           url_for("registration.admin_death_registrations"))


# ====================================================================
# 3. LICENSE REGISTRATION
# ====================================================================
@registration_bp.route("/license-registration", methods=["GET", "POST"])
@role_required("citizen")
def license_registration():
    if request.method == "POST":
        vehicle_id = request.form.get("vehicle_id", "").strip()
        test_id = request.form.get("test_id", "").strip()
        renewal_date_raw = request.form.get("renewal_date", "").strip()

        # Logged-in citizen is automatically the applicant.
        citizen_id = session["userId"]

        errors = []
        if not _required(vehicle_id):
            errors.append("Vehicle ID is required.")
        if not _required(test_id):
            errors.append("Test ID is required.")

        renewal_date = _parse_date(renewal_date_raw)
        if not renewal_date:
            errors.append("Please provide a valid renewal date (YYYY-MM-DD).")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("license_registration_form.html")

        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            # Duplicate check: same vehicle already has a Pending or Approved application.
            cursor.execute(
                """
                SELECT License_ID FROM License
                WHERE Vehicle_ID = %s AND Status IN ('Pending', 'Approved')
                """,
                (vehicle_id,)
            )
            if cursor.fetchone():
                flash("This vehicle already has a pending or approved license application.", "error")
                cursor.close()
                connection.close()
                return render_template("license_registration_form.html")

            cursor.execute(
                """
                INSERT INTO License (Vehicle_ID, Citizen_ID, Test_ID, Renewal_Date, Status)
                VALUES (%s, %s, %s, %s, 'Pending')
                """,
                (vehicle_id, citizen_id, test_id, renewal_date)
            )
            connection.commit()
            cursor.close()
            connection.close()

            flash("License application submitted successfully. Status: Pending.", "success")
            return redirect(url_for("registration.my_registrations"))

        except MySQLError:
            flash("Could not save the application. Please try again later.", "error")
            return render_template("license_registration_form.html")

    return render_template("license_registration_form.html")


@registration_bp.route("/admin/licenses", methods=["GET"])
@role_required("admin")
def admin_licenses():
    zone_min = zone_max = None
    try:
        zone_min, zone_max = get_admin_zone(session["userId"])
    except (ValueError, MySQLError) as exc:
        flash(f"Could not load your zone: {exc}", "error")
        return redirect(url_for("admin.dashboard"))

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT l.License_ID, l.Vehicle_ID, l.Citizen_ID, l.Test_ID,
                   l.Renewal_Date, l.Status, c.name AS citizen_name
            FROM License l
            LEFT JOIN Citizen c ON c.citizenId = l.Citizen_ID
            WHERE l.Citizen_ID BETWEEN %s AND %s
            ORDER BY FIELD(l.Status, 'Pending', 'Approved', 'Rejected'), l.Renewal_Date DESC
            """,
            (zone_min, zone_max)
        )
        records = cursor.fetchall()
        cursor.close()
        connection.close()
    except MySQLError:
        flash("Could not load license applications.", "error")
        records = []

    rows = [{
        "id": r["License_ID"],
        "status": r["Status"],
        "citizen_name": r["citizen_name"] or "Unknown",
        "citizen_id": r["Citizen_ID"],
        "fields": [
            ("Vehicle ID", r["Vehicle_ID"]),
            ("Test ID", r["Test_ID"]),
            ("Renewal Date", r["Renewal_Date"]),
        ],
    } for r in records]

    return render_template(
        "admin_registration_list.html",
        title="License Applications",
        rows=rows,
        approve_endpoint="registration.admin_license_action",
        zone_min=zone_min,
        zone_max=zone_max,
        back_url=url_for("admin.dashboard"),
    )


@registration_bp.route("/admin/licenses/<int:reg_id>/<action>", methods=["POST"])
@role_required("admin")
def admin_license_action(reg_id, action):
    return _update_status("License", "License_ID", reg_id, action,
                           url_for("registration.admin_licenses"))


# ====================================================================
# Shared: status update helper (used by all three Approve/Reject routes)
# ====================================================================
def _update_status(table, pk_column, record_id, action, redirect_url, citizen_col="Citizen_ID"):
    if action not in ("approve", "reject"):
        flash("Invalid action.", "error")
        return redirect(redirect_url)

    new_status = "Approved" if action == "approve" else "Rejected"

    zone_min = zone_max = None
    try:
        zone_min, zone_max = get_admin_zone(session["userId"])
    except (ValueError, MySQLError) as exc:
        flash(f"Could not verify your zone: {exc}", "error")
        return redirect(redirect_url)

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(f"SELECT {citizen_col} AS cid, Status FROM {table} WHERE {pk_column} = %s", (record_id,))
        record = cursor.fetchone()

        if not record:
            flash("Record not found.", "error")
        elif not (zone_min <= record["cid"] <= zone_max):
            flash("That record is not in your assigned zone.", "error")
        elif record["Status"] != "Pending":
            flash("This record has already been processed.", "error")
        else:
            cursor.execute(f"UPDATE {table} SET Status = %s WHERE {pk_column} = %s", (new_status, record_id))
            connection.commit()
            flash(f"Record #{record_id} marked as {new_status}.", "success")

        cursor.close()
        connection.close()

    except MySQLError:
        flash("Could not update the record. Please try again later.", "error")

    return redirect(redirect_url)


# ====================================================================
# Citizen: unified "My Registrations" view across all three modules
# ====================================================================
@registration_bp.route("/my-registrations", methods=["GET"])
@role_required("citizen")
def my_registrations():
    citizen_id = session["userId"]
    items = []

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT Birth_Reg_ID AS id, 'Birth Registration' AS type,
                   Birth_Date AS record_date, Status AS status
            FROM Birth_Registration
            WHERE Parent_Citizen_ID = %s
            """,
            (citizen_id,)
        )
        items.extend(cursor.fetchall())

        cursor.execute(
            """
            SELECT Death_Reg_ID AS id, 'Death Registration' AS type,
                   Death_Date AS record_date, Status AS status
            FROM Death_Registration
            WHERE Citizen_ID = %s
            """,
            (citizen_id,)
        )
        items.extend(cursor.fetchall())

        cursor.execute(
            """
            SELECT License_ID AS id, 'License Registration' AS type,
                   Renewal_Date AS record_date, Status AS status
            FROM License
            WHERE Citizen_ID = %s
            """,
            (citizen_id,)
        )
        items.extend(cursor.fetchall())

        cursor.execute(
            """
            SELECT Request_ID AS id, 'Sanitation Request' AS type,
                   Requested_Date AS record_date, Status AS status
            FROM Sanitation_Request
            WHERE Citizen_ID = %s
            """,
            (citizen_id,)
        )
        items.extend(cursor.fetchall())

        cursor.close()
        connection.close()

        items.sort(key=lambda i: (i["record_date"] is None, i["record_date"]), reverse=True)

    except MySQLError:
        flash("Could not load your registrations.", "error")

    return render_template("my_registrations.html", items=items)
