import sqlite3
from contextlib import closing

DB_PATH = "database/finance.db"


def get_connection():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    # Enable Foreign Keys
    conn.execute("PRAGMA foreign_keys = ON;")

    # Better concurrent performance
    conn.execute("PRAGMA journal_mode = WAL;")

    # Reasonable balance between speed and safety
    conn.execute("PRAGMA synchronous = NORMAL;")

    return conn


def init_db():

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT UNIQUE NOT NULL,
            country TEXT DEFAULT 'India',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            income REAL NOT NULL,
            expense REAL NOT NULL,
            risk TEXT NOT NULL,
            savings REAL NOT NULL,
            sip REAL NOT NULL,
            large_cap REAL NOT NULL,
            mid_cap REAL NOT NULL,
            small_cap REAL NOT NULL,
            emergency_fund REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)

        conn.commit()


def get_user_by_mobile(mobile):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE mobile = ?
            """,
            (mobile,)
        )

        return cursor.fetchone()


def create_user(name, mobile, country):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO users
            (
                name,
                mobile,
                country
            )
            VALUES (?, ?, ?)
            """,
            (
                name,
                mobile,
                country
            )
        )

        conn.commit()

        return cursor.lastrowid


def save_report(
    user_id,
    income,
    expense,
    risk,
    savings,
    sip,
    large_cap,
    mid_cap,
    small_cap,
    emergency_fund
):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO financial_reports
            (
                user_id,
                income,
                expense,
                risk,
                savings,
                sip,
                large_cap,
                mid_cap,
                small_cap,
                emergency_fund
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                income,
                expense,
                risk,
                savings,
                sip,
                large_cap,
                mid_cap,
                small_cap,
                emergency_fund
            )
        )

        conn.commit()


def get_all_reports():

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

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