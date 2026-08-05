"""
database.py
------------
Handles the MySQL connection for the whole app.
Uses mysql-connector-python (NOT SQLAlchemy, per project requirements).
"""

import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG


def get_db_connection():
    """
    Opens and returns a new MySQL connection using settings from config.py.
    Raises the underlying mysql.connector.Error if the connection fails,
    so callers can catch it and show a friendly error message.
    """
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
        )
        return connection
    except Error as e:
        # Re-raise so the calling route can handle/log it appropriately.
        raise e
