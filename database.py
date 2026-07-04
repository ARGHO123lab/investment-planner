import sqlite3

DB_PATH = "database/finance.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        mobile TEXT UNIQUE NOT NULL,
        country TEXT DEFAULT 'India',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Financial Reports Table
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
    conn.close()


def get_user_by_mobile(mobile):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE mobile = ?",
        (mobile,)
    )

    user = cursor.fetchone()

    conn.close()

    return user


def create_user(name, mobile, country):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO users (name, mobile, country)
        VALUES (?, ?, ?)
        """,
        (
            name,
            mobile,
            country
        )
    )

    conn.commit()

    user_id = cursor.lastrowid

    conn.close()

    return user_id


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

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
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
    ))

    conn.commit()
    conn.close()


def get_all_reports():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            users.name,
            users.mobile,
            users.country,
            financial_reports.*
        FROM financial_reports
        JOIN users
            ON users.id = financial_reports.user_id
        ORDER BY financial_reports.created_at DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows