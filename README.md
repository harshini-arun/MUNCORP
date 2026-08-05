# Municipal Corporation Management System — Phase 1 (Authentication Module)

This is **Phase 1** of the project: login, authentication, session
management, logout, and role-based dashboard skeletons for **Citizen**
and **Administrator**. No other municipal service module (Birth/Death
Registration, License, Tax, Grievance, Sanitation) is implemented yet —
they appear only as "Coming Soon" placeholder cards on the dashboards,
matching the full system design in `UseCase.jpg` / `ClassDiagram.jpg`.

## Tech Stack
- Python 3 / Flask (Blueprints)
- MySQL (via `mysql-connector-python`, no ORM)
- HTML5, CSS3, vanilla JavaScript, Bootstrap 5

## Project Structure
```
MunicipalCorporation/
├── app.py                     # App factory + root route
├── config.py                  # Secret key + DB connection settings
├── database.py                # MySQL connection helper
├── requirements.txt
├── municipal_corporation.sql  # DB schema + sample data
├── README.md
├── templates/
│   ├── layout.html
│   ├── login.html
│   ├── citizen_dashboard.html
│   └── admin_dashboard.html
├── static/
│   ├── css/style.css
│   ├── js/script.js
│   └── images/
└── routes/
    ├── auth.py     # login / logout / session + authorization decorators
    ├── citizen.py  # citizen dashboard + placeholder module routes
    └── admin.py    # admin dashboard + placeholder module routes
```

## Setup Instructions

### 1. Clone / unzip the project
```bash
cd MunicipalCorporation
```

### 2. Create a virtual environment (recommended)
```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up the MySQL database
Make sure MySQL is running locally, then run:
```bash
mysql -u root -p < municipal_corporation.sql
```
This creates the `municipal_corporation` database with `Citizen` and
`Admin` tables, and inserts one sample record in each.

### 5. Configure database credentials
Edit `config.py` (or set environment variables) with your MySQL
username/password:
```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_mysql_password",
    "database": "municipal_corporation",
}
```
You can also set `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and
`SECRET_KEY` as environment variables instead of editing the file.

### 6. Run the app
```bash
python app.py
```
Visit **http://127.0.0.1:5000** in your browser.

## Demo Credentials
| Role     | User ID | Password    |
|----------|---------|-------------|
| Citizen  | 1001    | password123 |
| Admin    | 1       | admin123    |

## Security Notes
- Passwords are stored as salted **scrypt hashes** (via
  `werkzeug.security`), not plain text, and compared with
  `check_password_hash()`.
- All SQL queries use **parameterized placeholders** (`%s`) — no string
  concatenation — to prevent SQL injection.
- Dashboard routes are protected by a `role_required()` decorator, so
  Citizens can't reach `/admin/*` and vice versa, and neither can be
  reached without logging in first.
- `SECRET_KEY` in `config.py` is a placeholder — set a strong random
  value via the `SECRET_KEY` environment variable before deploying
  anywhere beyond localhost.

## What's Next
Once this authentication module is verified end-to-end, the following
modules (already scoped out in `ClassDiagram.jpg`, `UseCase.jpg`, and
`ActivityDiagram.jpg`) will be added on top of it:
- Birth / Death Registration (with hospital certificate code verification)
- Vehicle License application & renewal
- Tax Payment (with tax calculation)
- Sanitation Request (with duplicate-priority ranking)
- Public Grievance (with approval-delay tracking)
