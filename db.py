import os
import mysql.connector
from mysql.connector import Error

def get_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("MYSQLHOST"),
            user=os.getenv("MYSQLUSER"),
            password=os.getenv("MYSQLPASSWORD"),
            database=os.getenv("MYSQLDATABASE"),
            port=int(os.getenv("MYSQLPORT", 4000)),
            ssl_verify_cert=False
        )

        if conn.is_connected():
            return conn

    except Error as e:
        print("Database connection failed:", e)
        return None
