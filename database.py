import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import closing

# DATABASE_URL is provided by your Render environment variables
DATABASE_URL = os.environ["DATABASE_URL"]

def get_connection():
    """
    Establishes a connection to the PostgreSQL database.
    RealDictCursor allows us to access columns by name (e.g., row['name']).
    """
    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )
    return conn

def init_db():
    """
    Schema initialization for PostgreSQL.
    Note: In production, you typically manage migrations via tools, 
    but this keeps your existing 'init_db' flow alive.
    """
    with closing(get_connection()) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                mobile TEXT UNIQUE NOT NULL,
                country TEXT DEFAULT 'India',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_reports (
                report_id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                income REAL NOT NULL,
                expense REAL NOT NULL,
                risk TEXT NOT NULL,
                savings REAL NOT NULL,
                sip REAL NOT NULL,
                large_cap REAL NOT NULL,
                mid_cap REAL NOT NULL,
                small_cap REAL NOT NULL,
                emergency_fund REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()

def get_user_by_mobile(mobile):
    with closing(get_connection()) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE mobile = %s",
                (mobile,)
            )
            return cursor.fetchone()

def create_user(name, mobile, country):
    with closing(get_connection()) as conn:
        with conn.cursor() as cursor:
            # RETURNING id is the PostgreSQL way to get the serial ID of the new row
            cursor.execute(
                """
                INSERT INTO users (name, mobile, country)
                VALUES (%s, %s, %s) RETURNING id
                """,
                (name, mobile, country)
            )
            conn.commit()
            return cursor.fetchone()['id']

def save_report(user_id, income, expense, risk, savings, sip, large_cap, mid_cap, small_cap, emergency_fund):
    with closing(get_connection()) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO financial_reports
                (user_id, income, expense, risk, savings, sip, large_cap, mid_cap, small_cap, emergency_fund)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, income, expense, risk, savings, sip, large_cap, mid_cap, small_cap, emergency_fund)
            )
            conn.commit()

def get_all_reports():
    with closing(get_connection()) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    users.name,
                    users.mobile,
                    users.country,
                    financial_reports.*
                FROM financial_reports
                INNER JOIN users
                    ON users.id = financial_reports.user_id
                ORDER BY financial_reports.created_at DESC
                """
            )
            return cursor.fetchall()