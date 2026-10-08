"""
routes/admin_utils.py
----------------------
Shared utilities for admin-side route modules.

get_admin_zone(admin_id)
    Returns (zone_min, zone_max) for the given admin from the Admin table.
    Raises ValueError if the admin is not found or has no zone configured.
    Caller is responsible for opening/closing the connection.
"""

from mysql.connector import Error as MySQLError
from database import get_db_connection


def get_admin_zone(admin_id):
    """
    Look up the citizen-ID range assigned to an admin.

    Returns:
        (zone_min: int, zone_max: int)

    Raises:
        ValueError  – admin not found or zone columns missing / NULL.
        MySQLError  – database connection or query error (propagated).
    """
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT zone_min, zone_max FROM Admin WHERE adminId = %s",
            (admin_id,)
        )
        row = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    if not row:
        raise ValueError(f"Admin {admin_id} not found in the database.")
    if row["zone_min"] is None or row["zone_max"] is None:
        raise ValueError(f"Admin {admin_id} has no citizen-ID zone configured.")
    return int(row["zone_min"]), int(row["zone_max"])
