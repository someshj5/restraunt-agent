import psycopg


DATABASE_URL = "postgresql://localhost/restaurant_agent"


def get_connection():
    return psycopg.connect(DATABASE_URL)