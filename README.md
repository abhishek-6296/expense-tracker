# Personal Expense Tracker

A simple full-stack web application where each user can securely track their
own income and expenses. Built to be easy to read, run, and explain in a
fresher technical interview.

## Tech stack

- **Python + Flask** — backend and routing
- **MySQL** (via `mysql-connector-python`) — database
- **HTML5, CSS3, Bootstrap 5** — frontend
- **Flask sessions** — keeps a user logged in
- **Werkzeug** — secure password hashing
- **Gunicorn** — production web server

## What it does

- Register, log in, and log out
- Dashboard showing total income, total expenses, and current balance
- Add, view, edit, and delete transactions
- Filter by type, category, and date; search by description
- Each user only ever sees their own data

---

## 1. Run it locally

### Step 1 — Install Python packages

```bash
pip install -r requirements.txt
```

### Step 2 — Create the database

Make sure MySQL is installed and running, then load the schema:

```bash
mysql -u root -p < schema.sql
```

This creates the `expense_tracker_db` database and the `users` and
`transactions` tables.

### Step 3 — Set up environment variables

Copy the example file and fill in your own values:

```bash
cp .env.example .env
```

Then open `.env` and set your MySQL password and a random `SECRET_KEY`.

### Step 4 — Start the app

```bash
python app.py
```

Open your browser at **http://localhost:5000**

---

## 2. Folder structure

```
expense-tracker/
├── app.py              # All routes and logic
├── db.py               # MySQL connection helper
├── schema.sql          # Database + table creation
├── requirements.txt    # Python dependencies
├── .env.example        # Sample environment variables
├── .gitignore          # Files Git should ignore
├── README.md
├── INTERVIEW_GUIDE.md  # Beginner-friendly explanations + Q&A
├── templates/          # HTML pages
└── static/             # CSS
```

---

## 3. Deploy to Railway

1. Push this project to a GitHub repository.
2. On [Railway](https://railway.app), create a new project from your repo.
3. Add a **MySQL** database plugin. Railway will provide the
   `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`, `MYSQLPASSWORD`, and
   `MYSQLDATABASE` variables automatically.
4. Add a `SECRET_KEY` variable with a long random value.
5. Set the **start command** to:

   ```
   gunicorn app:app
   ```

6. After the first deploy, run the contents of `schema.sql` against the
   Railway MySQL database to create the tables.

No passwords, credentials, or secret keys are hardcoded — everything is read
from environment variables.

---

## 4. Manual test checklist

1. Register a new user
2. Try registering again with the same email (should be rejected)
3. Log in with correct details
4. Log in with wrong details (should be rejected)
5. Log out
6. Add an income
7. Add an expense
8. Edit a transaction
9. Delete a transaction
10. Filter and search transactions
11. Check that the dashboard totals are correct
12. Log in as a second user and confirm you cannot see the first user's data
13. Try a negative or zero amount (should be rejected)
14. Restart the app — data is still there (it lives in MySQL)
