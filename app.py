import re
import os
import psycopg2
from psycopg2.extras import RealDictCursor
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

# PostgreSQL does not use a local file path, but kept for codebase consistency
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
    conn = psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=RealDictCursor
    )
    return conn

def extract_currency_symbol(country_name):
    country_data = COUNTRIES.get(country_name, '₹')
    if isinstance(country_data, dict):
        return country_data.get('currency_symbol', country_data.get('symbol', '₹'))
    return country_data

# NOTE: init_db logic is not needed as PostgreSQL schema is pre-managed in production
def init_db():
    pass 

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/delete/<int:article_id>', methods=['POST'])
@requires_auth
def delete_article(article_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM articles WHERE id = %s", (article_id,))
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
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE mobile=%s", (mobile,))

        existing_user = cur.fetchone()

        if existing_user:
            user_id = existing_user["id"]

            # Update latest details
            cur.execute("""
                UPDATE users
                SET name=%s, country=%s
                WHERE id=%s
            """, (
                name,
                country,
                user_id
            ))
            conn.commit()
        else:
            cur.execute("""
                INSERT INTO users(name,mobile,country)
                VALUES(%s,%s,%s) RETURNING id
            """, (
                name,
                mobile,
                country
            ))
            conn.commit()
            user_id = cur.fetchone()['id']

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
        income = float(request.form.get('income') or 0)
        expense = float(request.form.get('expense') or 0)
        risk = (request.form.get('risk') or 'medium').lower()
        savings = income - expense
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO reports (user_id, income, expense, savings, risk, created_at) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id", (user_id, income, expense, savings, risk, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        session['report_id'] = cur.fetchone()['id']
        conn.close()
        return redirect(url_for('dashboard'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
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
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO articles
            (title, slug, content)
            VALUES (%s, %s, %s)
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
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.execute(
        """
        SELECT *
        FROM reports
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id,)
    )
    report = cur.fetchone()
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
        P = float(request.form.get('monthly_investment') or 0)
        annual_return = float(request.form.get('annual_return') or 0)
        years = int(request.form.get('years') or 0)
        
        i = annual_return / 100 / 12
        n = years * 12
    
        if i == 0:
            fv = P * n
        else:
            fv = P * (((1 + i)**n - 1) / i) * (1 + i)
            
        result = "{:,.2f}".format(fv)
        if 'report_id' in session:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('UPDATE reports SET sip_calc_monthly = %s, sip_calc_years = %s, sip_calc_fv = %s WHERE id = %s', (P, years, fv, session['report_id']))
            conn.commit()
            conn.close()
    return render_template('sip_calculator.html', result=result)

@app.route('/financial-future', methods=['GET', 'POST'])
def financial_future():
    result = None
    if request.method == 'POST':
        age = int(request.form.get('age') or 0)
        target = float(request.form.get('target') or 0)
        years = int(request.form.get('years') or 0)
        
        months = years * 12
        m_rate = 0.12 / 12
        
        if months == 0 or target == 0:
            req_monthly = 0.0
        else:
            req_monthly = target / (((1 + m_rate)**months - 1) / m_rate) / (1 + m_rate)
            
        if 'user_id' in session:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("UPDATE users SET target_amount = %s, target_years = %s WHERE id = %s", (target, years, session['user_id']))
            if 'report_id' in session:
                cur.execute('UPDATE reports SET future_target_amount = %s, future_target_years = %s, future_req_monthly = %s WHERE id = %s', (target, years, req_monthly, session['report_id']))
            conn.commit()
            conn.close()
            
        result = {
            "monthly_total": "{:,.2f}".format(req_monthly), 
            "breakdown": {
                "sip": {"amount": "{:,.2f}".format(req_monthly * 0.4), "return": "12%"}, 
                "large": {"label": "Large Cap", "amount": "{:,.2f}".format(req_monthly * 0.3), "return": "10%"}, 
                "mid": {"label": "Mid Cap", "amount": "{:,.2f}".format(req_monthly * 0.2), "return": "15%"}, 
                "small": {"label": "Small Cap", "amount": "{:,.2f}".format(req_monthly * 0.1), "return": "18%"}
            }
        }
    return render_template('financial_future.html', result=result)

@app.route('/admin')
@requires_auth # <--- This locks the admin panel!
def admin():
    conn = get_db_connection()
    cur = conn.cursor()
    query = "SELECT r.id, u.name, u.mobile, u.country, r.income, r.expense, r.savings, r.risk, r.created_at, u.target_amount, u.target_years FROM reports r INNER JOIN users u ON r.user_id = u.id ORDER BY r.id DESC"
    cur.execute(query)
    rows = cur.fetchall()
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
    cur = conn.cursor()
    cur.execute("SELECT * FROM articles ORDER BY created_at DESC")
    articles = cur.fetchall()
    conn.close()
    return render_template('articles.html', articles=articles)

@app.route('/blog/<slug>')
def view_article(slug):
    conn = get_db_connection()
    cur = conn.cursor()
    # Query for the specific article
    cur.execute("SELECT * FROM articles WHERE slug = %s", (slug,))
    article = cur.fetchone()
    conn.close()
    
    # If no article is found, return a 404
    if article is None:
        return "Article not found", 404
        
    # If found, render the template
    return render_template('view_article.html', article=article)

@app.route("/disclaimer")
def disclaimer():
    return render_template("disclaimer.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/health")
def health():
    return {
        "status": "healthy",
        "application": "SmartPlan Finance",
        "version": "2.1"
    }, 200
@app.route("/sitemap.xml")
def sitemap():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT slug, created_at
        FROM articles
        ORDER BY created_at DESC
    """)

    articles = cursor.fetchall()
    conn.close()

    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    # Home page
    xml.append("""
    <url>
        <loc>https://smartplanfinance.com/</loc>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    """)

    # Blog listing
    xml.append("""
    <url>
        <loc>https://smartplanfinance.com/articles</loc>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>
    """)

    # Individual articles
    for article in articles:
        xml.append(f"""
        <url>
            <loc>https://smartplanfinance.com/blog/{article['slug']}</loc>
            <lastmod>{article['created_at']}</lastmod>
            <changefreq>monthly</changefreq>
            <priority>0.8</priority>
        </url>
        """)

    xml.append("</urlset>")

    return Response("\n".join(xml), mimetype="application/xml")
if __name__ == '__main__':
    # This runs only when you execute 'python app.py' locally
    # It will NOT override the production server settings
    app.run()