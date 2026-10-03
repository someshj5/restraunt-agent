from app.db.connection import get_connection


with get_connection() as conn:
    with conn.cursor() as cursor:

        cursor.execute("SELECT version();")

        result = cursor.fetchone()

        print(result)