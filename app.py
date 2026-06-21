import os
from datetime import date
from functools import wraps

import mysql.connector
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from db import get_db_connection

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

INCOME_CATEGORIES = ["Salary", "Freelance", "Business", "Other Income"]
EXPENSE_CATEGORIES = [
    "Food", "Transport", "Shopping", "Bills",
    "Education", "Health", "Entertainment", "Other Expense",
]
ALL_CATEGORIES = INCOME_CATEGORIES + EXPENSE_CATEGORIES


def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)
    return wrapped_view


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html")

        password_hash = generate_password_hash(password)

        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, password_hash),
            )
            connection.commit()
        except mysql.connector.IntegrityError:
            connection.rollback()
            flash("That email is already registered. Please log in.", "danger")
            return render_template("register.html")
        finally:
            cursor.close()
            connection.close()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("login.html")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")
        return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions "
        "WHERE user_id = %s AND type = 'Income'",
        (user_id,),
    )
    total_income = cursor.fetchone()["total"]

    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions "
        "WHERE user_id = %s AND type = 'Expense'",
        (user_id,),
    )
    total_expenses = cursor.fetchone()["total"]

    balance = total_income - total_expenses

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


@app.route("/transactions")
@login_required
def transactions():
    user_id = session["user_id"]

    filter_type = request.args.get("type", "").strip()
    filter_category = request.args.get("category", "").strip()
    filter_date = request.args.get("date", "").strip()
    search_text = request.args.get("search", "").strip()

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

    return render_template(
        "add_transaction.html",
        income_categories=INCOME_CATEGORIES,
        expense_categories=EXPENSE_CATEGORIES,
        today=date.today().isoformat(),
    )


@app.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit_transaction(transaction_id):
    user_id = session["user_id"]
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM transactions WHERE id = %s AND user_id = %s",
        (transaction_id, user_id),
    )
    transaction = cursor.fetchone()

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


@app.route("/transactions/<int:transaction_id>/delete", methods=["POST"])
@login_required
def delete_transaction(transaction_id):
    user_id = session["user_id"]
    connection = get_db_connection()
    cursor = connection.cursor()
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


def validate_transaction(t_type, amount_raw, category, transaction_date):
    if t_type not in ("Income", "Expense"):
        return "Please choose a valid type (Income or Expense)."

    if not category:
        return "Please choose a category."

    if not transaction_date:
        return "Please choose a transaction date."

    try:
        amount = float(amount_raw)
    except ValueError:
        return "Amount must be a number."

    if amount <= 0:
        return "Amount must be a positive number."

    return None


if __name__ == "__main__":
    app.run(debug=True)
