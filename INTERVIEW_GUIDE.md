# Interview Guide — Personal Expense Tracker

This guide explains the project in simple words. Read it once and you'll be
able to talk confidently about every part of the app.

---

## 1. Project purpose

The app lets a person keep track of money coming in (income) and money going
out (expenses). After logging in, they see their total income, total expenses,
and current balance, and they can add, edit, delete, filter, and search their
own transactions. Every user only sees their own data.

## 2. Technologies used

- **Python** — the programming language for the backend.
- **Flask** — a lightweight web framework that handles URLs and responses.
- **MySQL** — the database that stores users and transactions permanently.
- **mysql-connector-python** — the library Python uses to talk to MySQL.
- **HTML, CSS, Bootstrap 5** — build the pages and make them look clean.
- **Flask sessions** — remember who is logged in.
- **Werkzeug** — securely hashes passwords.
- **Gunicorn** — runs the app in production.

## 3. Complete application flow

1. A visitor opens the site and is sent to the login page.
2. They register an account (their password is hashed and saved).
3. They log in. Their user id is stored in the session.
4. They land on the dashboard with their totals.
5. They add, edit, delete, filter, and search transactions.
6. They log out, which clears the session.

## 4. Registration and login flow

**Registration:** the user submits name, email, password, and confirm
password. We check the fields are filled, the two passwords match, hash the
password, and insert a new row into the `users` table. If the email already
exists, MySQL's UNIQUE rule blocks it and we show a friendly message.

**Login:** the user submits email and password. We look up the user by email,
then use `check_password_hash` to compare the typed password with the stored
hash. If it matches, we save their user id in the session.

## 5. Password hashing

We never store the real password. During registration we call
`generate_password_hash(password)`, which turns the password into a long
scrambled string. During login we call
`check_password_hash(stored_hash, typed_password)`, which safely checks if the
typed password matches — without ever un-scrambling the stored value. This way,
even if someone saw the database, they could not read anyone's password.

## 6. Flask sessions

A session is a small piece of signed data stored in the user's browser cookie.
When someone logs in, we put their `user_id` in `session`. On every protected
page we check `if "user_id" not in session` and, if it's missing, send them
back to login. Logging out calls `session.clear()`.

## 7. MySQL connection

The file `db.py` has one function, `get_db_connection()`, which calls
`mysql.connector.connect()` using settings read from environment variables
(`MYSQLHOST`, `MYSQLPORT`, etc.). Each route opens a connection, runs its
query, and then closes the connection.

## 8. CRUD operations

CRUD means the four basic database actions:

- **Create** — add a new transaction (`INSERT`).
- **Read** — view transactions and totals (`SELECT`).
- **Update** — edit a transaction (`UPDATE`).
- **Delete** — remove a transaction (`DELETE`).

## 9. Primary key

A primary key is a column that uniquely identifies each row. In both tables the
`id` column is the primary key. It is `AUTO_INCREMENT`, so MySQL gives every new
row a new unique number automatically.

## 10. Foreign key

A foreign key links one table to another. In the `transactions` table, the
`user_id` column is a foreign key that points to `users(id)`. This means every
transaction must belong to a real user. `ON DELETE CASCADE` means if a user is
deleted, all their transactions are automatically deleted too.

## 11. One-to-many relationship

One user can have many transactions, but each transaction belongs to exactly
one user. That is a one-to-many relationship (one user → many transactions),
created through the `user_id` foreign key.

## 12. Parameterised queries

Instead of gluing user input straight into SQL text, we use placeholders
(`%s`) and pass the values separately, like:

```python
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
```

The database treats the values as plain data, never as commands. This protects
the app from **SQL injection** attacks.

## 13. How totals are calculated

We ask MySQL to add up the amounts for the logged-in user:

```sql
SELECT COALESCE(SUM(amount), 0) FROM transactions
WHERE user_id = %s AND type = 'Income';
```

`SUM` adds the amounts and `COALESCE(..., 0)` returns 0 when there are no rows.
We do the same for expenses, then in Python: `balance = total_income -
total_expenses`.

## 14. How user data is protected

- Every query includes `WHERE user_id = %s`, so a user only ever touches their
  own rows.
- Before editing or deleting, we confirm the transaction belongs to the current
  user.
- Protected pages check the session and redirect to login if no user is set.
- Passwords are hashed; only the user id is stored in the session.
- All queries are parameterised.

---

## 15. Twenty likely fresher interview questions (with simple answers)

1. **What is Flask?**
   A lightweight Python web framework for building web apps and APIs.

2. **What is a route in Flask?**
   A URL paired with a Python function that runs when that URL is visited.

3. **Difference between GET and POST?**
   GET is for fetching/showing pages; POST is for sending data that changes
   something (like creating or deleting).

4. **What is a template engine?**
   Flask uses Jinja2 to mix Python-like logic into HTML so pages can show
   dynamic data.

5. **What is `render_template`?**
   A Flask function that loads an HTML file from the `templates` folder and
   fills in the data we pass to it.

6. **Why hash passwords instead of storing them?**
   So that even if the database leaks, the real passwords can't be read.

7. **Difference between hashing and encryption?**
   Encryption can be reversed with a key; hashing is one-way and cannot be
   reversed.

8. **What is a Flask session?**
   A way to remember information (like the logged-in user) across requests using
   a signed cookie.

9. **Why store only the user id in the session?**
   It's small and safe; we can look up everything else from the database when
   needed.

10. **What is SQL injection and how do you prevent it?**
    A trick where bad input changes your SQL. We prevent it with parameterised
    queries using `%s` placeholders.

11. **What is a primary key?**
    A column that uniquely identifies each row (here, `id`).

12. **What is a foreign key?**
    A column that links to the primary key of another table (here, `user_id`).

13. **What is a one-to-many relationship?**
    One record relates to many others — one user, many transactions.

14. **What does `AUTO_INCREMENT` do?**
    Automatically gives each new row the next unique number.

15. **What is `ON DELETE CASCADE`?**
    When a parent row is deleted, its related child rows are deleted too.

16. **What does `commit()` do?**
    Saves the changes (insert/update/delete) permanently to the database.

17. **Why close the database connection?**
    To free up resources and avoid running out of connections.

18. **What is a flash message?**
    A short one-time message (like "Login successful") shown on the next page.

19. **How do you protect a page so only logged-in users can see it?**
    Check the session for `user_id`; if it's missing, redirect to login. We use
    a `login_required` decorator for this.

20. **What is Gunicorn and why use it?**
    A production-grade web server that runs the Flask app, handling many
    requests reliably (Flask's built-in server is only for development).

---

## 16. Five project limitations

1. No "forgot password" or email verification.
2. No pagination — a very long transaction list loads all at once.
3. Categories are fixed; users can't create their own.
4. No charts or graphs to visualise spending.
5. No automated test suite (testing is done manually).

## 17. Five future improvements

1. Add password reset via email.
2. Add monthly budgets and spending alerts.
3. Add simple charts to visualise income vs expenses.
4. Let users export their data to CSV.
5. Add pagination and sorting to the transactions table.

---

## Quick file-by-file recap

- **app.py** — every route lives here: register, login, logout, dashboard, and
  the add/view/edit/delete transaction logic, plus the `login_required` helper
  and the `validate_transaction` checker.
- **db.py** — opens a MySQL connection from environment variables.
- **schema.sql** — creates the database and the two tables.
- **templates/** — the HTML pages; `base.html` holds the shared navbar and the
  other pages extend it.
- **static/style.css** — small styling on top of Bootstrap.
- **requirements.txt / .env.example / .gitignore** — setup, configuration, and
  deployment files.
