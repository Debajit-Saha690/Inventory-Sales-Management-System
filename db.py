import mysql.connector
from mysql.connector import Error

def get_connection():

    """
    Creates and returns a MySQL database connection
    for Inventory Management System.
    """

    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="####",
            password="#####",
            database="stockflow_db"
        )

        if conn.is_connected():
            return conn

    except Error as e:
        print("Database connection failed:", e)
        return None
