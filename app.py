import re
import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, url_for, Response
from functools import wraps
from config import COUNTRIES

app = Flask(__name__)
# Make sure this matches your production environment
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "smartplanfinance-dev-secret"
)

# --- SECURITY GUARD (ADMIN AUTHENTICATION) ---
def check_auth(username, password):
    # This checks against the ADMIN_PASSWORD environment variable you set in Render
    return username == 'admin' and password == os.environ.get('ADMIN_PASSWORD')

def authenticate():
    return Response('Access Denied', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated
# ---------------------------------------------

DB_PATH = "database/finance.db"
print("Database Path:", os.path.abspath(DB_PATH))

RISK_RULES = {
    'low': {'sip': 0.3, 'large_cap': 0.4, 'mid_cap': 0.2, 'small_cap': 0.0, 'emergency': 0.1},
    'medium': {'sip': 0.4, 'large_cap': 0.3, 'mid_cap': 0.2, 'small_cap': 0.1, 'emergency': 0.0},
    'high': {'sip': 0.5, 'large_cap': 0.2, 'mid_cap': 0.2, 'small_cap': 0.1, 'emergency': 0.0}
}

ADVISOR_INSIGHTS = {
    'low': [
        "Your portfolio focuses heavily on stable assets like Large Cap funds.",
        "Consider building an emergency fund covering at least 3-6 months of expenses.",
        "Keep track of inflation; safe investments might yield lower real returns."
    ],
    'medium': [
        "Your asset distribution strikes a balanced approach between stability and growth.",
        "Periodic rebalancing is recommended to keep your allocation on track.",
        "A healthy mix of Mid Cap and Large Cap helps counter long-term market volatility."
    ],
    'high': [
        "High-risk profile means a greater focus on aggressive wealth maximization.",
        "Ensure you have a separate emergency backup so you aren't forced to sell equity during dips.",
        "Keep a long-term investment horizon (5+ years) to ride out market cycles."
    ]
}

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def extract_currency_symbol(country_name):
    country_data = COUNTRIES.get(country_name, '₹')
    if isinstance(country_data, dict):
        return country_data.get('currency_symbol', country_data.get('symbol', '₹'))
    return country_data

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Inside init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            country TEXT NOT NULL,
            target_amount REAL DEFAULT 0,
            target_years INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            income REAL NOT NULL,
            expense REAL NOT NULL,
            savings REAL NOT NULL,
            risk TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Add missing columns to USERS table
    user_columns = [
        ("target_amount", "REAL DEFAULT 0"),
        ("target_years", "INTEGER DEFAULT 0")
    ]

    for col_name, col_type in user_columns:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass

    # Add missing columns to REPORTS table
    report_columns = [
        ("sip_calc_monthly", "REAL DEFAULT 0"),
        ("sip_calc_years", "INTEGER DEFAULT 0"),
        ("sip_calc_fv", "REAL DEFAULT 0"),
        ("future_target_amount", "REAL DEFAULT 0"),
        ("future_target_years", "INTEGER DEFAULT 0"),
        ("future_req_monthly", "REAL DEFAULT 0")
    ]

    for col_name, col_type in report_columns:
        try:
            cursor.execute(f"ALTER TABLE reports ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/delete/<int:article_id>', methods=['POST'])
@requires_auth
def delete_article(article_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('articles'))
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        name = request.form.get('name')
        mobile = request.form.get('mobile')
        country = request.form.get('country')

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE mobile=?",
            (mobile,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            user_id = existing_user["id"]

            # Update latest details
            cursor.execute("""
                UPDATE users
                SET name=?, country=?
                WHERE id=?
            """, (
                name,
                country,
                user_id
            ))

            conn.commit()

        else:

            cursor.execute("""
                INSERT INTO users(name,mobile,country)
                VALUES(?,?,?)
            """, (
                name,
                mobile,
                country
            ))

            conn.commit()
            user_id = cursor.lastrowid

        conn.close()

        session["user_id"] = user_id
        session.pop("report_id", None)

        return redirect(url_for("profile"))

    return render_template(
        "login.html",
        countries=COUNTRIES.keys()
    )

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    if request.method == 'POST':
        income = float(request.form.get('income'))
        expense = float(request.form.get('expense'))
        risk = request.form.get('risk').lower()
        savings = income - expense
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reports (user_id, income, expense, savings, risk, created_at) VALUES (?, ?, ?, ?, ?, ?)", (user_id, income, expense, savings, risk, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        session['report_id'] = cursor.lastrowid
        conn.close()
        return redirect(url_for('dashboard'))
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return render_template('profile.html', name=user['name'], mobile=user['mobile'], country=user['country'])
@app.route('/publish', methods=['GET', 'POST'])
@requires_auth
def publish():

    if request.method == 'POST':

        title = request.form.get('title')
        content = request.form.get('content')

        # Generate SEO-friendly slug
        slug = re.sub(
            r'[^a-z0-9]+',
            '-',
            title.lower()
        ).strip('-')

        conn = get_db_connection()

        conn.execute(
            """
            INSERT INTO articles
            (title, slug, content)
            VALUES (?, ?, ?)
            """,
            (
                title,
                slug,
                content
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("articles"))

    return render_template("publish.html")
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    report = conn.execute(
    """
    SELECT *
    FROM reports
    WHERE user_id = ?
    ORDER BY created_at DESC
    LIMIT 1
    """,
    (user_id,)
).fetchone()
    conn.close()
    
    if not report: return redirect(url_for('profile'))
    
    savings = report['savings']
    risk = report['risk'].lower()
    rules = RISK_RULES.get(risk, RISK_RULES['medium'])
    currency = extract_currency_symbol(user['country'])
    
    # Calculate Dynamic Score
    savings_rate = (report['savings'] / report['income']) * 100 if report['income'] > 0 else 0
    score = int(40 + (savings_rate * 0.7)) 
    score = min(score, 99)
    
    # Merge everything into ONE dictionary
    report_data = {
        "country": user['country'], 
        "currency": currency, 
        "income": report['income'], 
        "expense": report['expense'], 
        "savings": savings, 
        "risk": risk.capitalize(), 
        "sip": savings * rules['sip'], 
        "large_cap": savings * rules['large_cap'], 
        "mid_cap": savings * rules['mid_cap'], 
        "small_cap": savings * rules['small_cap'], 
        "emergency_fund": savings * rules['emergency'], 
        "advice": ADVISOR_INSIGHTS.get(risk, []),
        "sip_calc_monthly": report['sip_calc_monthly'] or 0,
        "sip_calc_years": report['sip_calc_years'] or 0,
        "sip_calc_fv": report['sip_calc_fv'] or 0,
        "future_target_amount": report['future_target_amount'] or 0,
        "future_target_years": report['future_target_years'] or 0,
        "future_req_monthly": report['future_req_monthly'] or 0,
        "score": score # Score is now inside the same dictionary
    }
    
    return render_template('report.html', user=user, data=report_data)

@app.route('/sip-calculator', methods=['GET', 'POST'])
def sip_calculator():
    result = None
    if request.method == 'POST':
        P, i, n = float(request.form.get('monthly_investment')), float(request.form.get('annual_return'))/100/12, int(request.form.get('years'))*12
    
        fv = P * (((1 + i)**n - 1) / i) * (1 + i)
        result = "{:,.2f}".format(fv)
        if 'report_id' in session:
            conn = get_db_connection()
            conn.execute('UPDATE reports SET sip_calc_monthly = ?, sip_calc_years = ?, sip_calc_fv = ? WHERE id = ?', (P, request.form.get('years'), fv, session['report_id']))
            conn.commit()
            conn.close()
    return render_template('sip_calculator.html', result=result)

@app.route('/financial-future', methods=['GET', 'POST'])
def financial_future():
    result = None
    if request.method == 'POST':
        age, target, years = int(request.form.get('age')), float(request.form.get('target')), int(request.form.get('years'))
        months, m_rate = years * 12, 0.12 / 12
        req_monthly = target / (((1 + m_rate)**months - 1) / m_rate) / (1 + m_rate)
        if 'user_id' in session:
            conn = get_db_connection()
            conn.execute("UPDATE users SET target_amount = ?, target_years = ? WHERE id = ?", (target, years, session['user_id']))
            if 'report_id' in session:
                conn.execute('UPDATE reports SET future_target_amount = ?, future_target_years = ?, future_req_monthly = ? WHERE id = ?', (target, years, req_monthly, session['report_id']))
            conn.commit()
            conn.close()
        result = {"monthly_total": "{:,.2f}".format(req_monthly), "breakdown": {"sip": {"amount": "{:,.2f}".format(req_monthly * 0.4), "return": "12%"}, "large": {"label": "Large Cap", "amount": "{:,.2f}".format(req_monthly * 0.3), "return": "10%"}, "mid": {"label": "Mid Cap", "amount": "{:,.2f}".format(req_monthly * 0.2), "return": "15%"}, "small": {"label": "Small Cap", "amount": "{:,.2f}".format(req_monthly * 0.1), "return": "18%"}}}
    return render_template('financial_future.html', result=result)

@app.route('/admin')
@requires_auth # <--- This locks the admin panel!
def admin():
    conn = get_db_connection()
    query = "SELECT r.id, u.name, u.mobile, u.country, r.income, r.expense, r.savings, r.risk, r.created_at, u.target_amount, u.target_years FROM reports r INNER JOIN users u ON r.user_id = u.id ORDER BY r.id DESC"
    rows = conn.execute(query).fetchall()
    cleaned_reports = []
    for row in rows:
        r_dict = dict(row)
        if r_dict['name'].replace('-', '').replace('.', '').isdigit(): r_dict['name'] = f"User #{r_dict['id']}"
        cleaned_reports.append(r_dict)
    total_reports = len(cleaned_reports)
    high_risk, medium_risk, low_risk = sum(1 for r in cleaned_reports if r['risk'].lower() == 'high'), sum(1 for r in cleaned_reports if r['risk'].lower() == 'medium'), sum(1 for r in cleaned_reports if r['risk'].lower() == 'low')
    avg_income = sum(r['income'] for r in cleaned_reports) / total_reports if total_reports > 0 else 0
    avg_savings = sum(r['savings'] for r in cleaned_reports) / total_reports if total_reports > 0 else 0
    conn.close()
    return render_template('admin.html', total_reports=total_reports, high_risk=high_risk, medium_risk=medium_risk, low_risk=low_risk, avg_income="{:,.2f}".format(avg_income), avg_savings="{:,.2f}".format(avg_savings), reports=cleaned_reports)

@app.route('/articles')
def articles():
    conn = get_db_connection()
    articles = conn.execute("SELECT * FROM articles ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template('articles.html', articles=articles)

@app.route('/blog/<slug>')
def view_article(slug):
    conn = get_db_connection()
    # Query for the specific article
    article = conn.execute("SELECT * FROM articles WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    
    # If no article is found, return a 404
    if article is None:
        return "Article not found", 404
        
    # If found, render the template
    return render_template('view_article.html', article=article)
@app.route("/admin/delete-all-articles")
@requires_auth
def delete_all_articles():
    conn = get_db_connection()
    conn.execute("DELETE FROM articles")
    conn.commit()
    conn.close()
    return "✅ All articles deleted successfully."
@app.route("/health")
def health():
    return {
        "status": "healthy",
        "application": "SmartPlan Finance",
        "version": "2.1"
    }, 200
if __name__ == '__main__':
    # This runs only when you execute 'python app.py' locally
    # It will NOT override the production server settings
    app.run()