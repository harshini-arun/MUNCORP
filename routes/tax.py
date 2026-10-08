"""
routes/tax.py
--------------
Tax Payment module.

Flow (ActivityDiagram.jpg):
    Enter Property Value / Business Income
        -> Calculate Tax      (calculateTax(), a preview -- nothing stored)
        -> Confirm Payment    (makePayment())
        -> Store Transaction
        -> Generate Receipt

UseCase.jpg shows "Tax Payment <<include>> Calculate Tax", so the
calculation is a distinct step the citizen sees BEFORE committing: the
form posts to /tax-payment/calculate for a preview, and only the
confirmation screen writes a row. There is no admin approval for tax --
UseCase.jpg only gives the Administrator "View Tax Payment History".

Tax is recalculated server-side at confirmation time from the property
value / business income, never taken from the submitted form. Otherwise
a citizen could edit the hidden amount and pay whatever they liked.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from mysql.connector import Error as MySQLError

from database import get_db_connection
from routes.auth import role_required
from routes.admin_utils import get_admin_zone

tax_bp = Blueprint("tax", __name__)

# ---------------------------------------------------------------------
# Tax slabs. Illustrative rates for this project -- a real corporation
# would publish its own schedule; keeping them here in one place means
# the rules can be changed without touching the payment logic.
# ---------------------------------------------------------------------
PROPERTY_TAX_SLABS = [
    (Decimal("500000"),  Decimal("0.005")),   # up to 5L        -> 0.5%
    (Decimal("2000000"), Decimal("0.010")),   # 5L  - 20L       -> 1.0%
    (Decimal("5000000"), Decimal("0.015")),   # 20L - 50L       -> 1.5%
    (None,               Decimal("0.020")),   # above 50L       -> 2.0%
]

BUSINESS_TAX_SLABS = [
    (Decimal("300000"),  Decimal("0.010")),   # up to 3L        -> 1.0%
    (Decimal("1000000"), Decimal("0.020")),   # 3L  - 10L       -> 2.0%
    (Decimal("5000000"), Decimal("0.030")),   # 10L - 50L       -> 3.0%
    (None,               Decimal("0.040")),   # above 50L       -> 4.0%
]


def _rate_for(amount, slabs):
    """Returns the flat rate that applies to the whole amount."""
    for ceiling, rate in slabs:
        if ceiling is None or amount <= ceiling:
            return rate
    return slabs[-1][1]


def calculate_tax(tax_type, amount):
    """
    calculateTax() from ClassDiagram.jpg.
    Returns (tax_amount, rate) both as Decimals, rounded to 2 places.
    """
    slabs = PROPERTY_TAX_SLABS if tax_type == "Property" else BUSINESS_TAX_SLABS
    rate = _rate_for(amount, slabs)
    tax = (amount * rate).quantize(Decimal("0.01"))
    return tax, rate


def _parse_amount(raw):
    """Returns a positive Decimal, or None if the input isn't usable."""
    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, AttributeError, TypeError):
        return None
    if value <= 0 or value > Decimal("9999999999999"):
        return None
    return value


# ====================================================================
# Citizen: enter details
# ====================================================================
@tax_bp.route("/tax-payment", methods=["GET"])
@role_required("citizen")
def tax_payment():
    return render_template("tax_payment_form.html")


# ====================================================================
# Citizen: calculate (preview only -- nothing is stored yet)
# ====================================================================
@tax_bp.route("/tax-payment/calculate", methods=["POST"])
@role_required("citizen")
def calculate():
    tax_type = request.form.get("tax_type", "").strip()
    asset_id = request.form.get("asset_id", "").strip()
    amount_raw = request.form.get("amount", "").strip()

    errors = []
    if tax_type not in ("Property", "Business"):
        errors.append("Please choose Property Tax or Business Tax.")
    if not asset_id:
        errors.append("Property ID / Business ID is required.")

    amount = _parse_amount(amount_raw)
    if amount is None:
        label = "Property value" if tax_type == "Property" else "Business income"
        errors.append(f"{label} must be a positive number.")

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("tax_payment_form.html")

    tax_amount, rate = calculate_tax(tax_type, amount)

    return render_template(
        "tax_payment_confirm.html",
        tax_type=tax_type,
        asset_id=asset_id,
        amount=amount,
        tax_amount=tax_amount,
        rate_percent=(rate * 100).quantize(Decimal("0.01")),
    )


# ====================================================================
# Citizen: confirm + store the transaction
# ====================================================================
@tax_bp.route("/tax-payment/confirm", methods=["POST"])
@role_required("citizen")
def confirm():
    tax_type = request.form.get("tax_type", "").strip()
    asset_id = request.form.get("asset_id", "").strip()
    amount = _parse_amount(request.form.get("amount", ""))
    citizen_id = session["userId"]

    if tax_type not in ("Property", "Business") or not asset_id or amount is None:
        flash("Something went wrong with that payment. Please start again.", "error")
        return redirect(url_for("tax.tax_payment"))

    # Recalculate here rather than trusting any amount posted back from
    # the confirmation form.
    tax_amount, _ = calculate_tax(tax_type, amount)

    property_id = asset_id if tax_type == "Property" else None
    property_value = amount if tax_type == "Property" else None
    business_id = asset_id if tax_type == "Business" else None
    business_income = amount if tax_type == "Business" else None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO Tax_Payment
                (Citizen_ID, Tax_Type, Property_ID, Property_Value,
                 Business_ID, Business_Income, Tax_Amount, Payment_Date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (citizen_id, tax_type, property_id, property_value,
             business_id, business_income, tax_amount, date.today())
        )
        connection.commit()
        transaction_id = cursor.lastrowid
        cursor.close()
        connection.close()

        flash(f"Payment successful. Transaction #{transaction_id} recorded.", "success")
        return redirect(url_for("tax.receipt", transaction_id=transaction_id))

    except MySQLError:
        flash("Could not record the payment. Please try again later.", "error")
        return redirect(url_for("tax.tax_payment"))


# ====================================================================
# Citizen: receipt for one transaction (ownership enforced)
# ====================================================================
@tax_bp.route("/tax-payment/receipt/<int:transaction_id>", methods=["GET"])
@role_required("citizen")
def receipt(transaction_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT t.*, c.name AS citizen_name
            FROM Tax_Payment t
            LEFT JOIN Citizen c ON c.citizenId = t.Citizen_ID
            WHERE t.Transaction_ID = %s
            """,
            (transaction_id,)
        )
        record = cursor.fetchone()
        cursor.close()
        connection.close()
    except MySQLError:
        flash("Could not load that receipt.", "error")
        return redirect(url_for("tax.history"))

    # A citizen may only view their own receipts.
    if not record or record["Citizen_ID"] != session["userId"]:
        flash("Receipt not found.", "error")
        return redirect(url_for("tax.history"))

    return render_template("tax_receipt.html", r=record)


# ====================================================================
# Citizen: own payment history
# ====================================================================
@tax_bp.route("/tax-payment/history", methods=["GET"])
@role_required("citizen")
def history():
    records = []
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT Transaction_ID, Tax_Type, Property_ID, Property_Value,
                   Business_ID, Business_Income, Tax_Amount, Payment_Date
            FROM Tax_Payment
            WHERE Citizen_ID = %s
            ORDER BY Payment_Date DESC, Transaction_ID DESC
            """,
            (session["userId"],)
        )
        records = cursor.fetchall()
        cursor.close()
        connection.close()
    except MySQLError:
        flash("Could not load your payment history.", "error")

    return render_template("tax_history.html", records=records)


# ====================================================================
# Admin: all tax payments
# ====================================================================
@tax_bp.route("/admin/tax-payments", methods=["GET"])
@role_required("admin")
def admin_tax_payments():
    zone_min = zone_max = None
    try:
        zone_min, zone_max = get_admin_zone(session["userId"])
    except (ValueError, MySQLError) as exc:
        flash(f"Could not load your zone: {exc}", "error")
        return redirect(url_for("admin.dashboard"))

    records = []
    total = Decimal("0.00")
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT t.Transaction_ID, t.Citizen_ID, t.Tax_Type, t.Property_ID,
                   t.Property_Value, t.Business_ID, t.Business_Income,
                   t.Tax_Amount, t.Payment_Date, c.name AS citizen_name
            FROM Tax_Payment t
            LEFT JOIN Citizen c ON c.citizenId = t.Citizen_ID
            WHERE t.Citizen_ID BETWEEN %s AND %s
            ORDER BY t.Payment_Date DESC, t.Transaction_ID DESC
            """,
            (zone_min, zone_max)
        )
        records = cursor.fetchall()
        cursor.close()
        connection.close()
        total = sum((Decimal(str(r["Tax_Amount"])) for r in records), Decimal("0.00"))
    except MySQLError:
        flash("Could not load tax payments.", "error")

    return render_template(
        "admin_tax_list.html",
        records=records,
        total=total,
        zone_min=zone_min,
        zone_max=zone_max,
        back_url=url_for("admin.dashboard"),
    )
