"""
app.py
------
This is the heart of the application. It contains:

  * The Flask app setup
  * A small "login_required" helper to protect private pages
  * All the routes (URLs) for registration, login, logout,
    the dashboard, and the transactions CRUD (Create, Read, Update, Delete)

The code is intentionally simple so it is easy to read and explain.
"""

import os
from datetime import date
from functools import wraps

import mysql.connector
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
from werkzeug.security import generate_password_hash, check_password_hash

# Load variables from a local .env file during development.
# In production (Railway) the variables are provided by the platform,
# so this simply does nothing if there is no .env file.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from db import get_db_connection

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)

# The secret key is used by Flask to sign the session cookie securely.
# We read it from an environment variable so it is never hardcoded.
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

# The fixed list of categories used in the dropdowns.
INCOME_CATEGORIES = ["Salary", "Freelance", "Business", "Other Income"]
EXPENSE_CATEGORIES = [
    "Food", "Transport", "Shopping", "Bills",
    "Education", "Health", "Entertainment", "Other Expense",
]
ALL_CATEGORIES = INCOME_CATEGORIES + EXPENSE_CATEGORIES


# ---------------------------------------------------------------------------
# Helper: protect pages that require login
# ---------------------------------------------------------------------------
def login_required(view_function):
    """
    A decorator we place above any route that should only be visible
    to a logged-in user. If there is no user in the session, we send
    the visitor to the login page.
    """
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)
    return wrapped_view


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    # If already logged in, go straight to the dashboard.
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Read the form fields and remove extra spaces.
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # --- Validate all required fields ---
        if not name or not email or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html")

        # Hash the password so we never store it as plain text.
        password_hash = generate_password_hash(password)

        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            # Parameterised query protects us from SQL injection.
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, password_hash),
            )
            connection.commit()
        except mysql.connector.IntegrityError:
            # A duplicate email triggers the UNIQUE constraint.
            connection.rollback()
            flash("That email is already registered. Please log in.", "danger")
            return render_template("register.html")
        finally:
            cursor.close()
            connection.close()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    # GET request: just show the form.
    return render_template("register.html")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("login.html")

        connection = get_db_connection()
        # dictionary=True lets us read columns by name, e.g. user["id"].
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        # check_password_hash compares the typed password with the stored hash.
        if user and check_password_hash(user["password_hash"], password):
            # We store ONLY the user id (and name for greeting) in the session.
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")
        return render_template("login.html")

    return render_template("login.html")


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Total income for THIS user only.
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions "
        "WHERE user_id = %s AND type = 'Income'",
        (user_id,),
    )
    total_income = cursor.fetchone()["total"]

    # Total expenses for THIS user only.
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions "
        "WHERE user_id = %s AND type = 'Expense'",
        (user_id,),
    )
    total_expenses = cursor.fetchone()["total"]

    # Current balance = income - expenses.
    balance = total_income - total_expenses

    # The 5 most recent transactions for this user.
    cursor.execute(
        "SELECT * FROM transactions WHERE user_id = %s "
        "ORDER BY transaction_date DESC, id DESC LIMIT 5",
        (user_id,),
    )
    recent_transactions = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "dashboard.html",
        total_income=total_income,
        total_expenses=total_expenses,
        balance=balance,
        recent_transactions=recent_transactions,
    )


# ---------------------------------------------------------------------------
# Transactions list (with filter + search)
# ---------------------------------------------------------------------------
@app.route("/transactions")
@login_required
def transactions():
    user_id = session["user_id"]

    # Read the optional filter values from the URL query string.
    filter_type = request.args.get("type", "").strip()
    filter_category = request.args.get("category", "").strip()
    filter_date = request.args.get("date", "").strip()
    search_text = request.args.get("search", "").strip()

    # We build the WHERE clause piece by piece, always using placeholders.
    query = "SELECT * FROM transactions WHERE user_id = %s"
    params = [user_id]

    if filter_type in ("Income", "Expense"):
        query += " AND type = %s"
        params.append(filter_type)

    if filter_category:
        query += " AND category = %s"
        params.append(filter_category)

    if filter_date:
        query += " AND transaction_date = %s"
        params.append(filter_date)

    if search_text:
        query += " AND description LIKE %s"
        params.append(f"%{search_text}%")

    query += " ORDER BY transaction_date DESC, id DESC"

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template(
        "transactions.html",
        transactions=rows,
        categories=ALL_CATEGORIES,
        filter_type=filter_type,
        filter_category=filter_category,
        filter_date=filter_date,
        search_text=search_text,
    )


# ---------------------------------------------------------------------------
# Add a transaction
# ---------------------------------------------------------------------------
@app.route("/transactions/add", methods=["GET", "POST"])
@login_required
def add_transaction():
    if request.method == "POST":
        user_id = session["user_id"]
        t_type = request.form.get("type", "").strip()
        amount_raw = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        transaction_date = request.form.get("transaction_date", "").strip()

        # --- Validation ---
        error = validate_transaction(t_type, amount_raw, category, transaction_date)
        if error:
            flash(error, "danger")
            return render_template(
                "add_transaction.html",
                income_categories=INCOME_CATEGORIES,
                expense_categories=EXPENSE_CATEGORIES,
                today=date.today().isoformat(),
            )

        amount = float(amount_raw)

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO transactions "
            "(user_id, type, amount, category, description, transaction_date) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (user_id, t_type, amount, category, description, transaction_date),
        )
        connection.commit()
        cursor.close()
        connection.close()

        flash("Transaction added successfully.", "success")
        return redirect(url_for("transactions"))

    # GET: show the empty form.
    return render_template(
        "add_transaction.html",
        income_categories=INCOME_CATEGORIES,
        expense_categories=EXPENSE_CATEGORIES,
        today=date.today().isoformat(),
    )


# ---------------------------------------------------------------------------
# Edit a transaction
# ---------------------------------------------------------------------------
@app.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit_transaction(transaction_id):
    user_id = session["user_id"]
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Fetch the transaction AND check it belongs to the current user.
    cursor.execute(
        "SELECT * FROM transactions WHERE id = %s AND user_id = %s",
        (transaction_id, user_id),
    )
    transaction = cursor.fetchone()

    # If it does not exist or belongs to someone else, block access.
    if transaction is None:
        cursor.close()
        connection.close()
        flash("Transaction not found.", "danger")
        return redirect(url_for("transactions"))

    if request.method == "POST":
        t_type = request.form.get("type", "").strip()
        amount_raw = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        transaction_date = request.form.get("transaction_date", "").strip()

        error = validate_transaction(t_type, amount_raw, category, transaction_date)
        if error:
            flash(error, "danger")
            cursor.close()
            connection.close()
            return render_template(
                "edit_transaction.html",
                transaction=transaction,
                income_categories=INCOME_CATEGORIES,
                expense_categories=EXPENSE_CATEGORIES,
            )

        amount = float(amount_raw)

        # Update only if it still belongs to this user (extra safety).
        update_cursor = connection.cursor()
        update_cursor.execute(
            "UPDATE transactions SET type=%s, amount=%s, category=%s, "
            "description=%s, transaction_date=%s "
            "WHERE id=%s AND user_id=%s",
            (t_type, amount, category, description, transaction_date,
             transaction_id, user_id),
        )
        connection.commit()
        update_cursor.close()
        cursor.close()
        connection.close()

        flash("Transaction updated successfully.", "success")
        return redirect(url_for("transactions"))

    cursor.close()
    connection.close()
    return render_template(
        "edit_transaction.html",
        transaction=transaction,
        income_categories=INCOME_CATEGORIES,
        expense_categories=EXPENSE_CATEGORIES,
    )


# ---------------------------------------------------------------------------
# Delete a transaction
# ---------------------------------------------------------------------------
@app.route("/transactions/<int:transaction_id>/delete", methods=["POST"])
@login_required
def delete_transaction(transaction_id):
    user_id = session["user_id"]
    connection = get_db_connection()
    cursor = connection.cursor()
    # The "AND user_id = %s" makes sure a user can only delete their own row.
    cursor.execute(
        "DELETE FROM transactions WHERE id = %s AND user_id = %s",
        (transaction_id, user_id),
    )
    connection.commit()
    deleted = cursor.rowcount
    cursor.close()
    connection.close()

    if deleted:
        flash("Transaction deleted.", "success")
    else:
        flash("Transaction not found.", "danger")
    return redirect(url_for("transactions"))


# ---------------------------------------------------------------------------
# Shared validation helper
# ---------------------------------------------------------------------------
def validate_transaction(t_type, amount_raw, category, transaction_date):
    """
    Return an error message string if something is wrong,
    or None if everything is valid.
    """
    if t_type not in ("Income", "Expense"):
        return "Please choose a valid type (Income or Expense)."

    if not category:
        return "Please choose a category."

    if not transaction_date:
        return "Please choose a transaction date."

    # Amount must be a number AND must be positive.
    try:
        amount = float(amount_raw)
    except ValueError:
        return "Amount must be a number."

    if amount <= 0:
        return "Amount must be a positive number."

    return None


# ---------------------------------------------------------------------------
# Run locally (Gunicorn is used in production instead of this block)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
