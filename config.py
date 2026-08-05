"""
config.py
---------
Central configuration for the Flask application.
Edit the DB_CONFIG values to match your local MySQL setup.
"""

import os

# Secret key used to sign the Flask session cookie.
# In production, set this via an environment variable instead of hardcoding it.
SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")

# MySQL connection settings
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "Oracle23"),
    "database": os.environ.get("DB_NAME", "municipal_corporation"),
}
