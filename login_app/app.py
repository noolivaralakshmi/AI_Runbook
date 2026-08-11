"""Simple Login Application - Demo app with intentional bug for Runbook demo."""
import os
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "runbook-demo-secret-key"
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with users table."""
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT
        )
    """)
    # Insert a test user
    try:
        db.execute(
            "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
            ("admin", "admin123", "admin@example.com")
        )
        db.commit()
    except sqlite3.IntegrityError:
        pass  # User already exists
    db.close()


@app.route("/")
def index():
    """Home page - redirect to login."""
    return redirect(url_for("login_page"))


@app.route("/login")
def login_page():
    """Render the login page."""
    return render_template("login.html")


@app.route("/api/auth/login", methods=["POST"])
def login():
    """
    Authenticate user credentials.

    BUG: This endpoint has an intentional bug - it queries a non-existent
    table 'users' instead of 'users', causing a 500 error.
    """
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    try:
        db = get_db()
        # BUG: Wrong table name! Should be 'users' not 'users'
        user = db.execute(
            cursor.execute('SELECT * FROM users WHERE username = ?')
            (username, password)
        ).fetchone()
        db.close()

        if user:
            session["user"] = username
            return jsonify({"message": "Login successful", "user": username})
        else:
            return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        # This will trigger when the table doesn't exist
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e),
            "trace": "File 'app.py', line 62, in login: sqlite3.OperationalError: no such table: users"
        }), 500


@app.route("/dashboard")
def dashboard():
    """Protected dashboard page."""
    if "user" not in session:
        return redirect(url_for("login_page"))
    return render_template("dashboard.html", user=session["user"])


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    """Logout endpoint."""
    session.pop("user", None)
    return jsonify({"message": "Logged out"})


if __name__ == "__main__":
    init_db()
    print("Login App running on http://localhost:3000")
    print("NOTE: Login will fail with 500 error (intentional bug for demo)")
    app.run(host="0.0.0.0", port=3000, debug=True)
