"""
db.py
-----
A small helper file whose only job is to open a connection to MySQL.

We read all the database settings from environment variables so that we
never write passwords or secrets directly inside our code.
"""

import os
import mysql.connector


def get_db_connection():
    """
    Open and return a new MySQL connection.

    The caller is responsible for closing the connection when finished
    (we do this in every route after we are done with the database).
    """
    connection = mysql.connector.connect(
        host=os.environ.get("MYSQLHOST", "localhost"),
        port=int(os.environ.get("MYSQLPORT", 3306)),
        user=os.environ.get("MYSQLUSER", "root"),
        password=os.environ.get("MYSQLPASSWORD", ""),
        database=os.environ.get("MYSQLDATABASE", "expense_tracker_db"),
    )
    return connection
