from db import get_connection

conn = get_connection()

if conn:

    cursor = conn.cursor()

    cursor.execute("SELECT DATABASE();")

    print("Connected to:", cursor.fetchone())

    conn.close()

else:
    print("Connection Failed")