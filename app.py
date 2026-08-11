import re
import os
import uuid
import requests
import tempfile
import psycopg2
import psycopg2.pool
import hmac
import hashlib
import json
from collections import defaultdict, deque
from threading import Lock
from html import escape
from html.parser import HTMLParser
from psycopg2.extras import RealDictCursor
from io import BytesIO
from pathlib import Path

SITE_URL = "https://smartplanfinance.com"
DEFAULT_SEO_DESCRIPTION = (
    "SmartPlan Finance helps you build smarter investments, save tax, and plan your financial future "
    "with calculators, guides, and easy-to-use planning tools."
)
from datetime import datetime, timedelta
from flask import Flask, render_template, request, flash, redirect, send_file,session, url_for, Response
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Table, TableStyle, HRFlowable, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from functools import wraps
from config import COUNTRIES
from dotenv import load_dotenv
from functools import wraps
from flask import session, redirect, url_for
from flask import send_file
from pdf_generator import generate_financial_report
from flask import send_file
from openai import OpenAI
from datetime import date
import FAQ
import logging
from article_prompt import MASTER_ARTICLE_PROMPT
from flask import jsonify
from prompts import ARTICLE_PROMPT
from knowledge_base import INTERNAL_LINKS
import hmac
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from wellness import LITERACY_QUESTIONS, calculate_health_score, calculate_literacy_score, get_health_breakdown
from partner_links import PARTNER_LINKS, PAGE_PARTNER_MAP, KEYWORD_PARTNER_MAP
from flask import send_from_directory
from stock_analyzer import get_stock_data
from stock_ai import generate_stock_analysis
logging.basicConfig(level=logging.INFO)

load_dotenv(dotenv_path=Path(__file__).resolve().parent / '.env')

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
print("Groq Key Found:", GROQ_API_KEY is not None)
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)
app = Flask(__name__)
# Make sure this matches your production environment
app.secret_key = os.environ.get("SECRET_KEY")
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads", "articles")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
SECURITY_QUESTIONS = [
    "What was the name of your first pet?",
    "What is your mother's maiden name?",
    "What was the name of your first school?",
    "What city were you born in?",
]
from flask_wtf import CSRFProtect

csrf = CSRFProtect(app)
if not app.secret_key:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. "
        "The app will not start without it for security reasons."
    )

# Best-effort protection against automated use of the paid AI endpoint. This is
# deliberately independent of the per-session free-chat allowance below, which
# can otherwise be reset by clearing browser cookies. For multi-instance
# deployments, replace this in-memory store with Redis or another shared cache.
CHAT_RATE_LIMIT = 10
CHAT_RATE_WINDOW = timedelta(minutes=10)
_chat_attempts = defaultdict(deque)
_chat_rate_lock = Lock()
_ALLOWED_CHAT_TAGS = {"h4", "p", "ul", "li", "b", "strong", "em", "br"}


class _ChatHTMLSanitizer(HTMLParser):
    """Keep the small HTML subset used by the chat response and escape all else."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in _ALLOWED_CHAT_TAGS:
            self.parts.append(f"<{tag}>")

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self.parts.append("<br>")

    def handle_endtag(self, tag):
        if tag in _ALLOWED_CHAT_TAGS and tag != "br":
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        self.parts.append(escape(data))


def sanitize_chat_html(value):
    sanitizer = _ChatHTMLSanitizer()
    sanitizer.feed(value or "")
    sanitizer.close()
    return "".join(sanitizer.parts)


def _chat_rate_limited(client_ip):
    """Return True when an IP has exceeded the AI chat request limit."""
    now = datetime.utcnow()
    cutoff = now - CHAT_RATE_WINDOW

    with _chat_rate_lock:
        attempts = _chat_attempts[client_ip]
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()

        if len(attempts) >= CHAT_RATE_LIMIT:
            return True

        attempts.append(now)
        return False

# --- SECURITY GUARD (ADMIN AUTHENTICATION) ---
def generate_wellness_summary(health_score, literacy_score, literacy_total, breakdown_notes):

    if health_score >= 70:
        health_note = "You're in a strong position financially — keep up the good habits."
    elif health_score >= 40:
        health_note = "You're on a reasonable path, with some room to strengthen your savings and safety net."
    else:
        health_note = "There's good opportunity to build stronger financial habits, starting with your emergency fund and savings rate."

    if literacy_score >= (literacy_total * 0.7):
        lit_note = "Your financial knowledge is solid."
    else:
        lit_note = "Brushing up on a few core concepts could really help your planning."

    return f"""
    <p>{health_note}</p>
    <p>{lit_note}</p>
    <ul>
        <li>Explore our articles on budgeting, emergency funds, and SIP investing to build on your strengths.</li>
        <li>Small, consistent steps matter more than big changes all at once.</li>
    </ul>
    """
def generate_ai_advice(report):

    app.logger.info("===== AI FUNCTION STARTED =====")
    app.logger.info(f"API KEY EXISTS: {bool(GROQ_API_KEY)}")

    prompt = f"""
You are a Certified Financial Planner.

Analyze this person's finances.

Income: {report['income']}
Expense: {report['expense']}
Savings: {report['savings']}
Risk: {report['risk']}

Give:

1. Financial Health
2. Strengths
3. Weaknesses
4. Investment Suggestions
5. Emergency Fund Advice
6. Retirement Advice
7. Tax Saving Advice

Return only clean HTML.

Use:

<h3> for headings

<ul><li> for recommendations

<p> for paragraphs

Do NOT use Markdown.

Do NOT use **

Do NOT use numbered lists.

Do NOT return ```html
Maximum 300 words.
"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.5
    )
    print("Groq response received")
    return completion.choices[0].message.content

def generate_ai_article(topic):

    logging.info("===== AI ARTICLE GENERATION STARTED =====")
    logging.info(f"Topic: {topic}")

    try:

        prompt = MASTER_ARTICLE_PROMPT.format(
            topic=topic
        )

        completion = client.chat.completions.create(

            model="llama-3.1-8b-instant",

            messages=[
                {
                    "role": "system",
                    "content": """
You are the Chief Financial Editor of SmartPlan Finance.

Write SEO friendly financial education articles.

Return only HTML.

Keep article between 1200-1500 words.

Do not add META_TITLE.
Do not add META_DESCRIPTION.
Do not add KEYWORDS.

Only provide article HTML.
"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.45,

            max_tokens=3500
        )


        article = completion.choices[0].message.content

        return article


    except Exception as e:

        logging.error(
            f"AI ARTICLE ERROR: {str(e)}"
        )

        return """
        <h2>Article Generation Failed</h2>
        <p>Please try again.</p>
        """


    except Exception as e:

        logging.error(
            f"AI ARTICLE ERROR: {str(e)}"
        )

        return """
        <h2>Article Generation Failed</h2>
        <p>Please try again.</p>
        """
def generate_metadata(title, content):

    text = re.sub(
        "<.*?>",
        "",
        content
    )

    return {
        "meta_title": title[:60],
        "meta_description": text[:155],
        "keywords": "",
        "excerpt": text[:250],
        "reading_time": max(1, len(text.split()) // 200)
    }
def extract_article_data(ai_response):

    import re

    data = {
        "meta_title": "",
        "meta_description": "",
        "keywords": "",
        "excerpt": "",
        "reading_time": 0,
        "article_html": ""
    }


    if not ai_response:
        return data


    try:

        if "ARTICLE_HTML:" in ai_response:

            parts = ai_response.split(
                "ARTICLE_HTML:",
                1
            )


            header = parts[0]
            html = parts[1]


            data["article_html"] = html.strip()


            title = re.search(
                r"META_TITLE:\s*(.*?)\n\n",
                header,
                re.S
            )

            if title:
                data["meta_title"] = title.group(1).strip()



            description = re.search(
                r"META_DESCRIPTION:\s*(.*?)\n\n",
                header,
                re.S
            )

            if description:
                data["meta_description"] = description.group(1).strip()



            keywords = re.search(
                r"KEYWORDS:\s*(.*?)\n\n",
                header,
                re.S
            )

            if keywords:
                data["keywords"] = keywords.group(1).strip()



            excerpt = re.search(
                r"EXCERPT:\s*(.*?)\n\n",
                header,
                re.S
            )

            if excerpt:
                data["excerpt"] = excerpt.group(1).strip()



            reading = re.search(
                r"READING_TIME:\s*(\d+)",
                header
            )

            if reading:
                data["reading_time"] = int(
                    reading.group(1)
                )


        else:

            # fallback if AI returns only HTML
            data["article_html"] = ai_response



    except Exception as e:

        print(
            "ARTICLE PARSER ERROR:",
            e
        )

        data["article_html"] = ai_response



    return data
def generate_meta_description(title, content):

    text = re.sub("<.*?>", "", content)

    return text[:155]
def check_auth(username, password):
    # This checks against the ADMIN_PASSWORD environment variable you set in Render
    admin_password = os.environ.get('ADMIN_PASSWORD') or ''

    username_ok = hmac.compare_digest(username, 'admin')
    password_ok = hmac.compare_digest(password, admin_password)

    return username_ok and password_ok

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
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function
def get_latest_report(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM financial_reports
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id,))

    report = cursor.fetchone()

    conn.close()

    return report
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

DB_POOL = None
_ARTICLES_CACHE = None
_ARTICLES_CACHE_TIMESTAMP = None
_ARTICLES_HTML_CACHE = None
_ARTICLES_HTML_CACHE_TIMESTAMP = None
_ARTICLES_CACHE_TTL = 900  # seconds
_ARTICLE_PAGE_CACHE = {}
_ARTICLE_PAGE_CACHE_TTL = 900  # seconds


def invalidate_article_cache():
    """Drop rendered article pages immediately after editorial changes."""
    global _ARTICLES_CACHE, _ARTICLES_CACHE_TIMESTAMP
    global _ARTICLES_HTML_CACHE, _ARTICLES_HTML_CACHE_TIMESTAMP

    _ARTICLES_CACHE = None
    _ARTICLES_CACHE_TIMESTAMP = None
    _ARTICLES_HTML_CACHE = None
    _ARTICLES_HTML_CACHE_TIMESTAMP = None
    _ARTICLE_PAGE_CACHE.clear()


def get_db_connection():
    global DB_POOL
    if DB_POOL is None:
        DB_POOL = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=os.environ["DATABASE_URL"],
            cursor_factory=RealDictCursor,
        )
    return DB_POOL.getconn()


def release_db_connection(conn):
    if DB_POOL is not None and conn is not None:
        DB_POOL.putconn(conn)


def init_db_pool():
    conn = get_db_connection()
    release_db_connection(conn)


def get_cached_articles():
    global _ARTICLES_CACHE, _ARTICLES_CACHE_TIMESTAMP
    now = datetime.utcnow()
    if _ARTICLES_CACHE and _ARTICLES_CACHE_TIMESTAMP:
        if (now - _ARTICLES_CACHE_TIMESTAMP).total_seconds() < _ARTICLES_CACHE_TTL:
            return _ARTICLES_CACHE
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, title, slug, created_at,
                   LEFT(content, 500) AS excerpt
            FROM articles
            ORDER BY created_at DESC
            LIMIT 30
            """
        )
        articles = cur.fetchall()
        _ARTICLES_CACHE = articles
        _ARTICLES_CACHE_TIMESTAMP = now
        return articles
    finally:
        release_db_connection(conn)


def get_cached_articles_html():
    global _ARTICLES_HTML_CACHE, _ARTICLES_HTML_CACHE_TIMESTAMP
    now = datetime.utcnow()
    if _ARTICLES_HTML_CACHE and _ARTICLES_HTML_CACHE_TIMESTAMP:
        if (now - _ARTICLES_HTML_CACHE_TIMESTAMP).total_seconds() < _ARTICLES_CACHE_TTL:
            return _ARTICLES_HTML_CACHE
    articles = get_cached_articles()
    html = render_template('articles.html', articles=articles)
    _ARTICLES_HTML_CACHE = html
    _ARTICLES_HTML_CACHE_TIMESTAMP = now
    return html


def get_cached_article_page(slug):
    global _ARTICLE_PAGE_CACHE
    now = datetime.utcnow()
    cached = _ARTICLE_PAGE_CACHE.get(slug)
    if cached:
        html, timestamp = cached
        if (now - timestamp).total_seconds() < _ARTICLE_PAGE_CACHE_TTL:
            return html
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM articles
            WHERE slug = %s
            """,
            (slug,),
        )
        article = cur.fetchone()
        if article is None:
            return None

        # Use the latest articles as related suggestions instead of expensive keyword matching.
        cur.execute(
            """
            SELECT id,title,slug
            FROM articles
            WHERE slug != %s
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (slug,),
        )
        related_articles = cur.fetchall()

        html = render_template(
            'view_article.html',
            article=article,
            related_articles=related_articles,
            is_admin=False,
        )
        _ARTICLE_PAGE_CACHE[slug] = (html, now)
        return html
    finally:
        release_db_connection(conn)


def extract_currency_symbol(country_name):
    country_data = COUNTRIES.get(country_name, '₹')
    if isinstance(country_data, dict):
        return country_data.get('currency_symbol', country_data.get('symbol', '₹'))
    return country_data

# NOTE: init_db logic is not needed as PostgreSQL schema is pre-managed in production
def warm_up_article_cache():
    with app.app_context():
        try:
            with app.test_request_context('/articles'):
                get_cached_articles_html()

            conn = get_db_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT slug
                    FROM articles
                    ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()
                logging.info(f"Article warm-up: preloading {len(rows)} article pages")
                for row in rows:
                    slug = row.get("slug")
                    if slug:
                        with app.test_request_context(f"/blog/{slug}"):
                            get_cached_article_page(slug)
            finally:
                release_db_connection(conn)
        except Exception:
            logging.exception("Articles warm-up failed")


def init_db():
    init_db_pool()
    #warm_up_article_cache()

@app.route('/')
def index():
    return render_template('index.html')
@app.route("/reset-session")    
@requires_auth
def reset_session():
    session.clear()
    return "✅ Session cleared."
@app.route("/robots.txt")
def robots_txt():
    content = """User-agent: *
Allow: /

Sitemap: https://smartplanfinance.com/sitemap.xml
"""
    return Response(content, mimetype="text/plain")

@app.route("/chat", methods=["POST"])
def chat():
    # Get current chat count from Flask session
    chat_count = session.get("chat_count", 0)

    # Stop after 3 chats
    if chat_count >= 3:
        return jsonify({
            "reply": """
            <h4>Free Limit Reached</h4>
            <p>You have reached your free limit of <b>3 AI chats</b>.</p>
            <p>Please sign up or come back later.</p>
            """
        })

    payload = request.get_json(silent=True) or {}
    user_message = str(payload.get("message", "")).strip()

    if not user_message:
        return jsonify({"reply": "<p>Please enter a financial question.</p>"}), 400

    if len(user_message) > 500:
        return jsonify({"reply": "<p>Please keep your question to 500 characters or fewer.</p>"}), 400

    # request.remote_addr is intentionally used instead of a client-provided
    # forwarding header; configure ProxyFix at deployment time if behind a proxy.
    if _chat_rate_limited(request.remote_addr or "unknown"):
        return jsonify({
            "reply": "<p>Too many chat requests. Please wait a few minutes and try again.</p>"
        }), 429

    prompt = f"""
You are SmartPlan AI, the official AI assistant of SmartPlan Finance.

Your mission is to help people make better financial decisions.

You can answer questions about:
- Mutual Funds
- SIP
- Stocks
- Emergency Funds
- Retirement Planning
- Tax Planning
- Fixed Deposits
- Budgeting
- Financial Independence
- Insurance
- Personal Finance

Rules:

1. Answer in simple English.
2. Keep answers under 180 words.
3. Use HTML only.
4. Use:
<h4> for headings
<ul><li> for bullet points
<p> for paragraphs
5. Never use Markdown.
6. If someone asks a non-financial question, politely say:
"I'm SmartPlan AI and currently specialize in finance and investment-related questions."
7. Never guarantee returns.
8. Always encourage long-term investing.
9. If asked about specific stocks, remind users to do their own research.

Question:
{user_message}
"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5
        )

        # Increase chat count only after a successful AI response
        session["chat_count"] = chat_count + 1

        return jsonify({
            "reply": sanitize_chat_html(completion.choices[0].message.content)
        })

    except Exception as e:
        app.logger.error(f"Chatbot Error: {str(e)}")

        return jsonify({
            "reply": "<p>Sorry, something went wrong. Please try again later.</p>"
        }), 500
@app.route('/delete/<int:article_id>', methods=['POST'])
@requires_auth
def delete_article(article_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM articles WHERE id = %s", (article_id,))
    conn.commit()
    conn.close()
    invalidate_article_cache()
    return redirect(url_for('articles'))
@app.route("/loan-assistance", methods=["GET", "POST"])
def loan_assistance():

    success = False

    if request.method == "POST":

        full_name = request.form.get("full_name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        city = request.form.get("city")
        loan_type = request.form.get("loan_type")
        loan_amount = request.form.get("loan_amount")
        callback_time = request.form.get("callback_time")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""

            INSERT INTO loan_leads
            (
                full_name,
                phone,
                email,
                city,
                loan_type,
                loan_amount,
                callback_time
            )

            VALUES
            (%s,%s,%s,%s,%s,%s,%s)

        """,

        (
            full_name,
            phone,
            email,
            city,
            loan_type,
            loan_amount,
            callback_time
        ))

        conn.commit()

        cursor.close()
        conn.close()

        success = True

    return render_template('loan_assistance.html', success=success)
    
    return render_template('loan_assistance.html')

    
@app.route("/admin-loan-leads")
@requires_auth
def admin_loan_leads():

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute("""

        SELECT *

        FROM loan_leads

        ORDER BY created_at DESC

    """)

    leads = cursor.fetchall()

    conn.close()

    return render_template(

        "admin_loan_leads.html",

        leads=leads

    )
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():

    error = None

    if request.method == 'POST':

        mobile = request.form.get('mobile', '').strip()
        answer = request.form.get('security_answer', '').strip().lower()
        new_password = request.form.get('new_password', '').strip()

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id, security_answer_hash FROM users WHERE mobile = %s",
            (mobile,)
        )
        user = cur.fetchone()

        if not user or not user['security_answer_hash']:
            # Don't reveal whether the mobile number exists — just show a generic error
            error = "We couldn't verify those details. Please check and try again."

        elif not check_password_hash(user['security_answer_hash'], answer):
            error = "That answer doesn't match. Please try again."

        elif len(new_password) < 6:
            error = "New password must be at least 6 characters."

        else:
            new_hash = generate_password_hash(new_password, method="pbkdf2:sha256")

            cur.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (new_hash, user['id'])
            )
            conn.commit()
            conn.close()

            return redirect(url_for('login'))

        conn.close()

    return render_template('forgot_password.html', error=error)
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        name = request.form.get('name')
        mobile = request.form.get('mobile')
        country = request.form.get('country')
        password = request.form.get('password')

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id, password_hash FROM users WHERE mobile = %s",
            (mobile,)
        )

        existing_user = cur.fetchone()

        if existing_user:

            stored_hash = existing_user["password_hash"]
            user_id = existing_user["id"]

            if not stored_hash:
                # Old account with no password yet — don't just accept any typed
                # password as "proof" it's really them. Block login and tell them
                # to contact support to set up their password securely.
                conn.close()
                return render_template(
                    "login.html",
                    countries=COUNTRIES.keys(),
                    security_questions=SECURITY_QUESTIONS,
                    error="Your account needs a password set up. Please contact support."
                )

            elif not check_password_hash(stored_hash, password):
                # Existing password doesn't match what they typed.
                conn.close()
                return render_template(
                    "login.html",
                    countries=COUNTRIES.keys(),
                    security_questions=SECURITY_QUESTIONS,
                    error="Incorrect mobile number or password."
                )

            # Update latest user details (but never overwrite the password here)
            cur.execute("""
                UPDATE users
                SET name = %s,
                    country = %s
                WHERE id = %s
            """, (
                name,
                country,
                user_id
            ))

            conn.commit()

        else:

            # New user - create their account with a securely hashed password
            password_hash = generate_password_hash(password, method="pbkdf2:sha256")
            security_question = request.form.get('security_question', '').strip()
            security_answer = request.form.get('security_answer', '').strip().lower()
            security_answer_hash = generate_password_hash(security_answer, method="pbkdf2:sha256") if security_answer else None

            cur.execute("""
                INSERT INTO users
                (
                    name,
                    mobile,
                    country,
                    password_hash,
                    security_question,
                    security_answer_hash
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING id
            """, (
                name,
                mobile,
                country,
                password_hash,
                security_question,
                security_answer_hash
            ))

            conn.commit()

            user_id = cur.fetchone()["id"]

        conn.close()

        session["user_id"] = user_id

        return redirect(url_for("profile"))

    return render_template(
        "login.html",
        countries=COUNTRIES.keys(),
        security_questions=SECURITY_QUESTIONS
    )

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    if request.method == 'POST':

        income = float(request.form.get('income') or 0)
        expense = float(request.form.get('expense') or 0)
        risk = (request.form.get('risk') or 'medium').lower()

        savings = income - expense

        conn = get_db_connection()
        cur = conn.cursor()

        # Check if a report already exists for this user
        cur.execute(
            "SELECT id FROM reports WHERE user_id = %s",
            (user_id,)
        )
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE reports
                SET income = %s,
                    expense = %s,
                    savings = %s,
                    risk = %s,
                    created_at = %s
                WHERE user_id = %s
            """,
            (
                income,
                expense,
                savings,
                risk,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user_id
            ))
        else:
            cur.execute("""
                INSERT INTO reports
                (user_id, income, expense, savings, risk, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                income,
                expense,
                savings,
                risk,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM users WHERE id = %s",
        (user_id,)
    )

    user = cur.fetchone()

    conn.close()

    return render_template(
        'profile.html',
        name=user['name'],
        mobile=user['mobile'],
        country=user['country']
    )
@app.route("/admin/edit-article/<int:article_id>", methods=["GET", "POST"])
@requires_auth
def edit_article(article_id):

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get article
    cur.execute(
        """
        SELECT *
        FROM articles
        WHERE id = %s
        """,
        (article_id,)
    )

    article = cur.fetchone()

    if article is None:
        conn.close()
        return "Article not found", 404

    # Save changes
    if request.method == "POST":

        title = request.form.get("title", "").strip()
        meta_description = request.form.get("meta_description", "").strip()
        content = request.form.get("content", "").strip()

        # Generate meta description if empty
        if not meta_description:
            plain_text = re.sub("<.*?>", "", content)
            meta_description = plain_text[:155]

        # Generate SEO slug
        slug = re.sub(
            r"[^a-z0-9]+",
            "-",
            title.lower()
        ).strip("-")

        # Update article
        cur.execute(
            """
            UPDATE articles
            SET
                title = %s,
                slug = %s,
                content = %s,
                meta_description = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                title,
                slug,
                content,
                meta_description,
                article_id
            )
        )

        conn.commit()
        conn.close()
        invalidate_article_cache()

        return redirect(
            url_for(
                "view_article",
                slug=slug
            )
        )

    conn.close()

    return render_template(
        "edit_article.html",
        article=article
    )
@app.route("/admin/upload-featured-image/<int:article_id>", methods=["GET", "POST"])
@requires_auth
def upload_featured_image(article_id):

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == "POST":

        if "image" not in request.files:
            cur.close()
            conn.close()
            return "No image selected."

        image = request.files["image"]

        if image.filename == "":
            cur.close()
            conn.close()
            return "No image selected."

        filename = secure_filename(image.filename)

        # Ensure upload directory exists
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

        # Absolute file path
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        print("=" * 60)
        print("Saving image to:", filepath)
        print("=" * 60)

        image.save(filepath)

        # Store relative path in database
        image_path = f"/static/uploads/articles/{filename}"

        cur.execute(
            """
            UPDATE articles
            SET featured_image = %s
            WHERE id = %s
            """,
            (image_path, article_id)
        )

        conn.commit()

        # Get slug for redirect
        cur.execute(
            """
            SELECT slug
            FROM articles
            WHERE id = %s
            """,
            (article_id,)
        )

        article = cur.fetchone()

        cur.close()
        conn.close()
        invalidate_article_cache()

        return redirect(
            url_for(
                "view_article",
                slug=article["slug"]
            )
        )

    # GET request
    cur.execute(
        """
        SELECT id, title, slug, featured_image
        FROM articles
        WHERE id = %s
        """,
        (article_id,)
    )

    article = cur.fetchone()

    cur.close()
    conn.close()

    if article is None:
        return "Article not found.", 404

    return render_template(
        "upload_featured_image.html",
        article=article,
        article_id=article_id
    )
@app.route('/publish', methods=['GET', 'POST'])
@requires_auth
def publish():

    # -----------------------------
    # OPEN PAGE
    # -----------------------------
    if request.method == "GET":

        return render_template(
            "publish.html",
            generated_title="",
            generated_content="",
            generated_meta=""
        )


    action = request.form.get("action")


    # ==========================================================
    # AI ARTICLE GENERATION
    # ==========================================================
    if action == "generate":

        topic = request.form.get(
            "ai_topic",
            ""
        ).strip()


        if not topic:

            return render_template(
                "publish.html",
                generated_title="",
                generated_content="<p>Please enter an article topic.</p>",
                generated_meta=""
            )


        # Generate article using AI
        article_html = generate_ai_article(topic)


        # Safety check
        if not article_html:

            article_html = """
            <h2>Article Generation Failed</h2>
            <p>
            AI did not return any content.
            Please try again.
            </p>
            """


        # Add internal links
        article_html = add_internal_links(
            article_html
        )


        # Generate SEO meta description
        meta_description = generate_meta_description(
            topic,
            article_html
        )


        return render_template(
            "publish.html",
            generated_title=topic,
            generated_content=article_html,
            generated_meta=meta_description
        )



    # ==========================================================
    # PUBLISH ARTICLE TO DATABASE
    # ==========================================================

    title = request.form.get(
        "title",
        ""
    ).strip()


    content = request.form.get(
        "content",
        ""
    ).strip()


    meta_description = request.form.get(
        "meta_description",
        ""
    ).strip()



    # Generate meta description if empty
    if not meta_description:

        meta_description = generate_meta_description(
            title,
            content
        )


    # Create SEO slug
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
        (
            title,
            slug,
            content,
            meta_description
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            title,
            slug,
            content,
            meta_description
        )
    )


    conn.commit()

    conn.close()
    invalidate_article_cache()


    return redirect(
        url_for(
            "view_article",
            slug=slug
        )
    )

def add_internal_links(content):

    # ----------------------------------
    # Calculator Links
    # ----------------------------------

    internal_links = {

        "SIP Calculator": "/sip-calculator",
        "SIP": "/sip-calculator",

        "EMI Calculator": "/emi_calculator",
        "EMI": "/emi_calculator",

        "Retirement Calculator": "/retirement_calculator",
        "Retirement": "/retirement_calculator",

        "FD Calculator": "/fd_calculator",
        "FD": "/fd_calculator",
        "Fixed Deposit": "/fd_calculator",

        "Tax Calculator": "/tax_calculator",
        "Tax": "/tax_calculator",

        "Financial Planner": "/financial-future",
        "Financial Goal": "/financial-future",

        "SmartPlan Finance": "/"

    }


    # ----------------------------------
    # Add Calculator Links
    # ----------------------------------

    for text, url in internal_links.items():

        if f'href="{url}"' in content:
            continue


        pattern = rf"\b{text}\b"


        replacement = (
            f'<a href="{url}" '
            f'style="color:#B8860B;font-weight:600;">'
            f'{text}</a>'
        )


        content = re.sub(
            pattern,
            replacement,
            content,
            count=1,
            flags=re.IGNORECASE
        )



    # ----------------------------------
    # Add Related Article Links
    # ----------------------------------

    try:

        conn = get_db_connection()
        cur = conn.cursor()


        cur.execute(
            """
            SELECT title, slug
            FROM articles
            ORDER BY created_at DESC
            LIMIT 20
            """
        )


        articles = cur.fetchall()

        conn.close()



        for article in articles:

            title = article["title"]
            slug = article["slug"]


            # Avoid empty titles

            if len(title) < 10:
                continue


            if f"/blog/{slug}" in content:
                continue



            pattern = rf"\b{re.escape(title)}\b"



            replacement = (
                f'<a href="/blog/{slug}" '
                f'style="color:#B8860B;font-weight:600;">'
                f'{title}</a>'
            )


            content = re.sub(
                pattern,
                replacement,
                content,
                count=1,
                flags=re.IGNORECASE
            )


    except Exception as e:

        logging.error(
            f"Article linking error: {e}"
        )


    return content



@app.route('/dashboard')
@login_required
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
        "emi_loan_amount": report["emi_loan_amount"] or 0,
"emi_rate": report["emi_rate"] or 0,
"emi_years": report["emi_years"] or 0,
"emi_monthly": report["emi_monthly"] or 0,
"emi_interest": report["emi_interest"] or 0,
"emi_total": report["emi_total"] or 0,
"retirement_corpus": report["retirement_corpus"] or 0,
"retirement_monthly": report["retirement_monthly"] or 0,
"retirement_age": report["retirement_age"] or 0,
"fd_principal": report["fd_principal"] or 0,
"fd_rate": report["fd_rate"] or 0,
"fd_years": report["fd_years"] or 0,
"fd_interest": report["fd_interest"] or 0,
"fd_maturity": report["fd_maturity"] or 0,
"tax_income": report["tax_income"] or 0,
"tax_old": report["tax_old"] or 0,
"tax_new": report["tax_new"] or 0,
"tax_savings": report["tax_savings"] or 0,
"tax_better": report["tax_better"] or "",
        "score": score # Score is now inside the same dictionary
    }
    #report_data["ai_advice"] = generate_ai_advice(report_data)
    report_data["ai_advice"] = None

    

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
            fv = P * (((1 + i) ** n - 1) / i) * (1 + i)

        result = "{:,.2f}".format(fv)

        

    return render_template(
    'sip_calculator.html',
    result=result,
    partners=PAGE_PARTNER_MAP.get('sip_calculator', []),
    PARTNER_LINKS=PARTNER_LINKS
)
@app.route('/networth-calculator', methods=['GET', 'POST'])
def networth_calculator():
    """
    NetWorth Calculator - Calculate total net worth by tracking assets and liabilities
    Formula: Net Worth = Total Assets - Total Liabilities
    """
    result = None
    breakdown = None
    status = None
    error = None

    if request.method == 'POST':
        try:
            # Assets - Convert form data to float with 0 as default
            real_estate = float(request.form.get('real_estate', 0) or 0)
            vehicles = float(request.form.get('vehicles', 0) or 0)
            savings_account = float(request.form.get('savings_account', 0) or 0)
            current_investments = float(request.form.get('current_investments', 0) or 0)
            retirement_account = float(request.form.get('retirement_account', 0) or 0)
            business_value = float(request.form.get('business_value', 0) or 0)
            other_assets = float(request.form.get('other_assets', 0) or 0)

            # Liabilities - Convert form data to float with 0 as default
            mortgage = float(request.form.get('mortgage', 0) or 0)
            auto_loan = float(request.form.get('auto_loan', 0) or 0)
            personal_loan = float(request.form.get('personal_loan', 0) or 0)
            credit_card_debt = float(request.form.get('credit_card_debt', 0) or 0)
            student_loan = float(request.form.get('student_loan', 0) or 0)
            other_liabilities = float(request.form.get('other_liabilities', 0) or 0)

            # Calculate totals
            total_assets = (real_estate + vehicles + savings_account + 
                          current_investments + retirement_account + 
                          business_value + other_assets)
            
            total_liabilities = (mortgage + auto_loan + personal_loan + 
                               credit_card_debt + student_loan + other_liabilities)

            # Calculate net worth
            net_worth = total_assets - total_liabilities

            # Create breakdown for display (only include items with values)
            breakdown = {
                'assets': {
                    'real_estate': real_estate,
                    'vehicles': vehicles,
                    'savings_account': savings_account,
                    'current_investments': current_investments,
                    'retirement_account': retirement_account,
                    'business_value': business_value,
                    'other_assets': other_assets,
                    'total': total_assets
                },
                'liabilities': {
                    'mortgage': mortgage,
                    'auto_loan': auto_loan,
                    'personal_loan': personal_loan,
                    'credit_card_debt': credit_card_debt,
                    'student_loan': student_loan,
                    'other_liabilities': other_liabilities,
                    'total': total_liabilities
                }
            }

            # Format result for display
            result = "{:,.2f}".format(net_worth)
            
            # Determine net worth status
            if net_worth > 0:
                status = "positive"
            elif net_worth < 0:
                status = "negative"
            else:
                status = "neutral"

        except (ValueError, TypeError) as e:
            error = "Please enter valid numbers in all fields"
            result = None
            breakdown = None
            status = None

    return render_template(
        'networth_calculator.html',
        result=result,
        breakdown=breakdown,
        status=status,
        error=error,
        
    )
import json
from functools import lru_cache
 
# For XIRR calculation
try:
    from scipy.optimize import newton
except ImportError:
    newton = None
 
 
def calculate_xirr(cash_flows, guess=0.1):
    """
    Calculate XIRR (Extended Internal Rate of Return)
    
    Args:
        cash_flows: List of tuples (date, amount)
                   First date should be earliest, last should be latest
        guess: Initial guess for rate (default 0.1 = 10%)
    
    Returns:
        XIRR as decimal (e.g., 0.158 = 15.8%)
    """
    if not cash_flows or len(cash_flows) < 2:
        return 0
    
    # Sort by date
    sorted_flows = sorted(cash_flows, key=lambda x: x[0])
    
    # Get the first date as reference
    ref_date = sorted_flows[0][0]
    
    # Calculate days from reference date
    def npv(rate):
        total = 0
        for date, amount in sorted_flows:
            days = (date - ref_date).days
            years = days / 365.0
            if years == 0:
                total += amount
            else:
                total += amount / ((1 + rate) ** years)
        return total
    
    # Use Newton-Raphson method to find the rate
    if newton:
        try:
            # Calculate derivative for Newton-Raphson
            def npv_derivative(rate):
                h = 0.0001
                return (npv(rate + h) - npv(rate - h)) / (2 * h)
            
            xirr = newton(npv, guess, fprime=npv_derivative, maxiter=100)
            return xirr
        except:
            # Fallback to simple iteration
            return calculate_xirr_iterative(cash_flows)
    else:
        return calculate_xirr_iterative(cash_flows)
 
 
def calculate_xirr_iterative(cash_flows, guess=0.1, max_iterations=100, tolerance=0.0001):
    """
    Fallback XIRR calculation using iterative method (no scipy required)
    """
    if not cash_flows or len(cash_flows) < 2:
        return 0
    
    sorted_flows = sorted(cash_flows, key=lambda x: x[0])
    ref_date = sorted_flows[0][0]
    
    def npv(rate):
        total = 0
        for date, amount in sorted_flows:
            days = (date - ref_date).days
            years = days / 365.0
            if years == 0:
                total += amount
            else:
                total += amount / ((1 + rate) ** years)
        return total
    
    # Newton-Raphson iteration
    rate = guess
    for _ in range(max_iterations):
        npv_val = npv(rate)
        if abs(npv_val) < tolerance:
            break
        
        # Numerical derivative
        h = 0.0001
        npv_derivative = (npv(rate + h) - npv(rate - h)) / (2 * h)
        
        if npv_derivative == 0:
            break
        
        rate = rate - npv_val / npv_derivative
        
        # Prevent extreme values
        if rate > 2:
            rate = 2
        elif rate < -0.99:
            rate = -0.99
    
    return rate
 
 
def generate_xirr_insights(xirr, total_invested, current_value, duration_years, absolute_return):
    """
    Generate AI-powered insights for XIRR results
    """
    insights = []
    xirr_percentage = xirr * 100
    inflation_rate = 6.0  # India's typical inflation
    
    # Main performance insight
    if xirr_percentage > inflation_rate + 8:  # > 14%
        insights.append(
            f"Exceptional performance! Your portfolio has delivered an annualized return of {xirr_percentage:.1f}%, "
            f"significantly outperforming the inflation rate. This indicates excellent investment discipline and timing."
        )
    elif xirr_percentage > inflation_rate + 4:  # 10-14%
        insights.append(
            f"Strong performance! Your portfolio has generated an annualized return of {xirr_percentage:.1f}%, "
            f"comfortably beating inflation. You're on track for consistent wealth creation."
        )
    elif xirr_percentage > inflation_rate:  # 6-10%
        insights.append(
            f"Moderate performance with {xirr_percentage:.1f}% annualized returns. While beating inflation, "
            f"consider reviewing your asset allocation for potentially higher returns."
        )
    else:
        insights.append(
            f"Your portfolio's annualized return of {xirr_percentage:.1f}% is not keeping pace with inflation. "
            f"Revisit your investment strategy and allocation mix."
        )
    
    # Duration insight
    if duration_years >= 15:
        insights.append(
            "Long-term investing commitment detected! Your investment horizon has allowed compound growth to work effectively. "
            "Continuing this discipline will likely amplify your wealth over time."
        )
    elif duration_years >= 5:
        insights.append(
            f"Over {duration_years} years of investing shows good discipline. Maintain consistency and avoid panic selling "
            f"during market downturns to maximize long-term returns."
        )
    else:
        insights.append(
            "Your investment duration is relatively short. Longer time horizons typically improve XIRR due to market cycles. "
            "Consider extending your investment timeline for better returns."
        )
    
    # Cash flow insight
    if total_invested > 0:
        average_annual_invested = total_invested / max(duration_years, 1)
        insights.append(
            f"You've invested ₹{total_invested:,.0f} over your investment period (₹{average_annual_invested:,.0f}/year). "
            f"Consider stepping up your investments by 10% annually to accelerate wealth creation."
        )
    
    # Profit insight
    if absolute_return > 0:
        profit_percentage = (absolute_return / total_invested) * 100 if total_invested > 0 else 0
        insights.append(
            f"Total profit generated: ₹{absolute_return:,.0f} ({profit_percentage:.0f}% absolute return). "
            f"This demonstrates the power of staying invested and allowing compounding to work."
        )
    
    # Next steps
    insights.append(
        "Monitor your portfolio quarterly, rebalance annually, and ensure your asset allocation aligns with your risk profile. "
        "Avoid chasing high returns and focus on consistent, disciplined investing."
    )
    
    return insights
@app.route('/xirr-calculator', methods=['GET', 'POST'])
def xirr_calculator():
    """
    XIRR Calculator Route
    Calculate Extended Internal Rate of Return for portfolios with multiple cash flows
    """
    result = None
    
    if request.method == 'POST':
        try:
            # Parse cash flows from form
            dates = request.form.getlist('date[]')
            amounts = request.form.getlist('amount[]')
            current_value = float(request.form.get('current_value', 0))
            
            # Convert to proper format
            cash_flows = []
            for date_str, amount_str in zip(dates, amounts):
                if date_str and amount_str:
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        amount = float(amount_str)
                        # Negative for investments (outflows)
                        cash_flows.append((date_obj, -amount if amount > 0 else amount))
                    except ValueError:
                        continue
            
            # Add current value as final inflow
            if cash_flows and current_value > 0:
                # Use today's date for current value
                from datetime import date as date_type
                cash_flows.append((date_type.today(), current_value))
            
            if len(cash_flows) >= 2:
                # Calculate XIRR
                xirr = calculate_xirr(cash_flows)
                
                # Calculate metrics
                total_invested = sum(abs(cf[1]) for cf in cash_flows[:-1])
                absolute_return = current_value - total_invested
                
                # Calculate duration
                if len(cash_flows) >= 2:
                    start_date = min(cf[0] for cf in cash_flows)
                    end_date = max(cf[0] for cf in cash_flows)
                    duration_days = (end_date - start_date).days
                    duration_years = duration_days / 365.0
                else:
                    duration_years = 0
                
                # Annualized return percentage
                annualized_return = xirr * 100
                
                # Absolute return percentage
                absolute_return_pct = (absolute_return / total_invested * 100) if total_invested > 0 else 0
                
                # Generate insights
                insights = generate_xirr_insights(xirr, total_invested, current_value, duration_years, absolute_return)
                
                # Determine performance badge
                if annualized_return > 18:
                    badge = "🔥"
                    performance = "Outstanding"
                elif annualized_return > 14:
                    badge = "⭐"
                    performance = "Excellent"
                elif annualized_return > 10:
                    badge = "👍"
                    performance = "Good"
                elif annualized_return > 6:
                    badge = "📈"
                    performance = "Fair"
                else:
                    badge = "⚠️"
                    performance = "Below Average"
                
                result = {
                    'xirr': f"{annualized_return:.2f}",
                    'xirr_value': annualized_return,
                    'total_invested': f"{total_invested:,.2f}",
                    'current_value': f"{current_value:,.2f}",
                    'absolute_return': f"{absolute_return:,.2f}",
                    'absolute_return_pct': f"{absolute_return_pct:.2f}",
                    'duration_days': duration_days,
                    'duration_years': f"{duration_years:.1f}",
                    'num_transactions': len(cash_flows) - 1,
                    'badge': badge,
                    'performance': performance,
                    'insights': insights,
                    'confidence': min(95, int(80 + (duration_years * 2)))  # Higher for longer periods
                }
        
        except Exception as e:
            # Return error message
            result = {'error': str(e)}
    
    return render_template(
        'xirr_calculator.html',
        result=result,
        partners=PAGE_PARTNER_MAP.get("xirr_calculator", []),
        PARTNER_LINKS=PARTNER_LINKS
    )

@app.route('/loan-eligibility-calculator', methods=['GET', 'POST'])
def loan_eligibility_calculator():
    """
    Loan Eligibility Calculator Route
    Calculate loan eligibility based on income, debt, credit score, and employment type
    """
    result = None
    
    if request.method == 'POST':
        try:
            # Parse form data
            annual_income = float(request.form.get('annual_income', 0))
            monthly_expenses = float(request.form.get('monthly_expenses', 0))
            existing_loan_emi = float(request.form.get('existing_loan_emi', 0))
            credit_score = int(request.form.get('credit_score', 0))
            employment_type = request.form.get('employment_type', 'salaried')
            desired_loan_amount = float(request.form.get('desired_loan_amount', 0))
            loan_tenure_years = int(request.form.get('loan_tenure_years', 20))
            
            # Validate inputs
            if annual_income <= 0:
                raise ValueError("Annual income must be greater than 0")
            if credit_score < 300 or credit_score > 900:
                raise ValueError("Credit score must be between 300-900")
            
            # Calculate monthly income
            monthly_income = annual_income / 12
            
            # Determine base interest rate based on credit score and employment type
            if credit_score >= 750:
                base_rate = 6.5 if employment_type == 'salaried' else 7.5
            elif credit_score >= 700:
                base_rate = 7.5 if employment_type == 'salaried' else 8.5
            elif credit_score >= 650:
                base_rate = 8.5 if employment_type == 'salaried' else 9.5
            else:
                base_rate = 10.0 if employment_type == 'salaried' else 11.5
            
            # Calculate maximum monthly loan EMI at 50% debt-to-income ratio
            max_monthly_obligations = monthly_income * 0.50
            available_for_new_loan = max_monthly_obligations - (monthly_expenses + existing_loan_emi)
            
            # Calculate maximum eligible loan amount
            # Using EMI formula: EMI = P * [r(1+r)^n] / [(1+r)^n - 1]
            # where P = principal, r = monthly rate, n = months
            if available_for_new_loan > 0:
                monthly_rate = base_rate / 100 / 12
                months = loan_tenure_years * 12
                
                # Reverse EMI calculation to find maximum principal
                if monthly_rate > 0:
                    max_eligible_loan = available_for_new_loan * ((1 + monthly_rate) ** months - 1) / (monthly_rate * (1 + monthly_rate) ** months)
                else:
                    max_eligible_loan = available_for_new_loan * months
            else:
                max_eligible_loan = 0
            
            # Calculate EMI for desired loan amount
            if desired_loan_amount > 0:
                monthly_rate = base_rate / 100 / 12
                months = loan_tenure_years * 12
                
                if monthly_rate > 0:
                    desired_loan_emi = desired_loan_amount * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
                else:
                    desired_loan_emi = desired_loan_amount / months
                
                # Calculate total interest
                total_repayment = desired_loan_emi * months
                total_interest = total_repayment - desired_loan_amount
            else:
                desired_loan_emi = 0
                total_interest = 0
                total_repayment = 0
            
            # Calculate DTI ratio with new loan
            new_total_obligations = monthly_expenses + existing_loan_emi + desired_loan_emi
            dti_ratio = (new_total_obligations / monthly_income) * 100 if monthly_income > 0 else 0
            
            # Determine eligibility status and approval probability
            if max_eligible_loan <= 0:
                eligibility_status = "Needs Improvement"
                eligibility_color = "#FF6B6B"
                approval_probability = 5
            elif desired_loan_amount > max_eligible_loan:
                eligibility_status = "Moderate"
                eligibility_color = "#FFC107"
                # Approval probability based on how much over limit
                over_limit_percent = ((desired_loan_amount - max_eligible_loan) / max_eligible_loan) * 100
                approval_probability = max(20, 70 - (over_limit_percent * 0.5))
            elif dti_ratio > 60:
                eligibility_status = "Moderate"
                eligibility_color = "#FFC107"
                approval_probability = 60
            else:
                eligibility_status = "Eligible"
                eligibility_color = "#4CAF50"
                approval_probability = min(95, 85 + (credit_score - 700) / 20)
            
            # Employment type multiplier for approval probability
            if employment_type == 'self-employed':
                approval_probability *= 0.85
            elif employment_type == 'business':
                approval_probability *= 0.80
            
            approval_probability = max(5, min(99, approval_probability))
            
            # Generate insights
            insights = []
            
            # Insight 1: Credit Score
            if credit_score >= 750:
                insights.append("✓ Excellent credit score! You qualify for the best interest rates available.")
            elif credit_score >= 700:
                insights.append("✓ Good credit score. You can access competitive interest rates. Focus on maintaining this score.")
            elif credit_score >= 650:
                insights.append("⚠ Your credit score is fair. Consider improving it to access better rates (each 50-point increase saves ₹5-8K annually).")
            else:
                insights.append("⚠ Low credit score. Work on improving it before applying. Pay bills on time and reduce credit utilization.")
            
            # Insight 2: DTI Ratio
            if dti_ratio <= 35:
                insights.append("✓ Your debt-to-income ratio is excellent ({}%). Lenders will view you favorably.".format(int(dti_ratio)))
            elif dti_ratio <= 50:
                insights.append("✓ Your DTI ratio is healthy ({}%). You have good borrowing capacity.".format(int(dti_ratio)))
            elif dti_ratio <= 60:
                insights.append("⚠ Your DTI is at {}%. Consider reducing existing obligations before taking new loans.".format(int(dti_ratio)))
            else:
                insights.append("⚠ Your DTI exceeds 60%. Focus on paying down existing loans first.")
            
            # Insight 3: Loan affordability
            if desired_loan_amount <= max_eligible_loan:
                savings_vs_max = max_eligible_loan - desired_loan_amount
                insights.append("✓ Your desired loan amount is well within your eligibility. You have ₹{:,.0f} additional borrowing capacity.".format(savings_vs_max))
            else:
                over_by = desired_loan_amount - max_eligible_loan
                insights.append("⚠ Your desired loan exceeds eligibility by ₹{:,.0f}. Consider reducing tenure to 15-18 years or loan amount.".format(over_by))
            
            # Insight 4: Tenure impact
            if loan_tenure_years <= 15:
                insights.append("✓ Shorter tenure ({}y) means less total interest. You'll build equity faster.".format(loan_tenure_years))
            elif loan_tenure_years <= 20:
                insights.append("✓ {} year tenure balances monthly payment with reasonable interest cost.".format(loan_tenure_years))
            else:
                insights.append("⚠ {} year tenure increases total interest paid. Each additional year adds ₹{:,.0f} in interest.".format(
                    loan_tenure_years, 
                    desired_loan_amount * 0.06 * 12  # Approximate interest cost per year
                ))
            
            # Employment type insight
            if employment_type == 'self-employed':
                insights.append("ℹ As self-employed, maintain 2 years ITR and consistent income proof for faster approval.")
            elif employment_type == 'business':
                insights.append("ℹ As business owner, lenders will closely review business financials. Keep detailed records.")
            
            result = {
                'annual_income': f"{annual_income:,.0f}",
                'monthly_income': f"{monthly_income:,.0f}",
                'credit_score': credit_score,
                'employment_type': employment_type.capitalize(),
                'estimated_interest_rate': f"{base_rate:.2f}",
                'dti_ratio': f"{dti_ratio:.1f}",
                'dti_ratio_value': dti_ratio,
                'max_eligible_loan': f"{max_eligible_loan:,.0f}",
                'max_eligible_loan_value': max_eligible_loan,
                'desired_loan_amount': f"{desired_loan_amount:,.0f}",
                'desired_loan_emi': f"{desired_loan_emi:,.0f}",
                'total_interest': f"{total_interest:,.0f}",
                'total_repayment': f"{total_repayment:,.0f}",
                'loan_tenure_years': loan_tenure_years,
                'eligibility_status': eligibility_status,
                'eligibility_color': eligibility_color,
                'approval_probability': f"{approval_probability:.0f}",
                'approval_probability_value': approval_probability,
                'insights': insights,
                'confidence': min(95, int(70 + (credit_score / 10)))
            }
        
        except Exception as e:
            result = {'error': str(e)}
    
    return render_template(
        'loan_eligibility_calculator.html',
        result=result,
        partners=PAGE_PARTNER_MAP.get("loan_eligibility_calculator", []),
        PARTNER_LINKS=PARTNER_LINKS
    )
from math import pow

@app.route("/swp_calculator", methods=["GET", "POST"])
def swp_calculator():

    result = None

    if request.method == "POST":

        try:

            corpus = float(request.form["corpus"])
            withdrawal = float(request.form["withdrawal"])
            annual_return = float(request.form["return_rate"])
            inflation = float(request.form.get("inflation", 6))
            yearly_increase = float(request.form.get("stepup", 5))
            years = int(request.form["years"])

            monthly_rate = annual_return / 100 / 12

            balance = corpus

            total_withdrawn = 0

            yearly_data = []

            current_withdrawal = withdrawal

            months_completed = 0

            for year in range(1, years + 1):

                for month in range(12):

                    balance *= (1 + monthly_rate)

                    if balance >= current_withdrawal:

                        balance -= current_withdrawal
                        total_withdrawn += current_withdrawal

                    else:

                        total_withdrawn += balance
                        balance = 0

                    months_completed += 1

                    if balance <= 0:
                        break

                yearly_data.append({

                    "year": year,
                    "withdrawal": round(current_withdrawal * 12, 2),
                    "balance": round(balance, 2)

                })

                current_withdrawal *= (1 + yearly_increase / 100)

                if balance <= 0:
                    break

            future_value = corpus * pow((1 + inflation / 100), years)

            safe_monthly = (corpus * 0.04) / 12

            withdrawal_ratio = withdrawal / safe_monthly

            if withdrawal_ratio <= 1:

                sustainability = "Excellent"
                badge = "🟢"
                confidence = 95

            elif withdrawal_ratio <= 1.25:

                sustainability = "Good"
                badge = "🟡"
                confidence = 82

            elif withdrawal_ratio <= 1.5:

                sustainability = "Needs Attention"
                badge = "🟠"
                confidence = 65

            else:

                sustainability = "High Risk"
                badge = "🔴"
                confidence = 40

            net_gain = total_withdrawn + balance - corpus

            stepup_percent = f"{yearly_increase:.0f}%"

            insights = [

                f"Your SWP lasted approximately {round(months_completed/12,1)} years.",

                f"A monthly withdrawal of around ₹{safe_monthly:,.0f} is generally considered more sustainable for long-term investing.",

                "Review your withdrawal amount every year instead of increasing it suddenly.",

                "Maintain 12-24 months of expenses in liquid investments to avoid selling equity during market downturns.",

                "Inflation gradually reduces purchasing power. Review your retirement plan annually.",

                "Diversifying across equity and debt funds can improve long-term SWP sustainability."

            ]

            strategy = [

                "Increase withdrawals gradually every year.",

                "Review your portfolio annually.",

                "Avoid panic selling during market corrections.",

                "Rebalance your asset allocation once a year.",

                "Invest surplus income separately to extend retirement corpus."

            ]

            result = {

                "corpus": round(corpus,2),

                "remaining": round(balance,2),

                "withdrawn": round(total_withdrawn,2),

                "interest": round(net_gain,2),

                "years_completed": round(months_completed/12,1),

                "future_value": round(future_value,2),

                "safe_monthly": round(safe_monthly,2),

                "current_withdrawal": round(withdrawal,2),

                "confidence": confidence,

                "badge": badge,

                "sustainability": sustainability,

                "stepup": stepup_percent,

                "yearly_data": yearly_data,

                "insights": insights,

                "strategy": strategy

            }

        except Exception as e:

            result = {

                "error": str(e)

            }

    return render_template(

        "swp_calculator.html",

        result=result,

        partners=PAGE_PARTNER_MAP.get("swp_calculator", []),

        PARTNER_LINKS=PARTNER_LINKS

    )
from math import pow

@app.route("/lumpsum_calculator", methods=["GET", "POST"])
def lumpsum_calculator():

    result = None

    if request.method == "POST":

        try:

            investment = float(request.form["investment"])
            annual_return = float(request.form["return_rate"])
            years = float(request.form["years"])

            future_value = investment * pow((1 + annual_return / 100), years)

            wealth_gained = future_value - investment

            yearly_growth = []

            for year in range(1, int(years) + 1):

                value = investment * pow((1 + annual_return / 100), year)

                yearly_growth.append({
                    "year": year,
                    "value": round(value, 2)
                })

            result = {
                "investment": round(investment, 2),
                "future_value": round(future_value, 2),
                "wealth_gained": round(wealth_gained, 2),
                "return_rate": annual_return,
                "years": years,
                "yearly_growth": yearly_growth
            }

        except Exception as e:

            result = {
                "error": str(e)
            }

    return render_template(
    "lumpsum_calculator.html",
    result=result,
    partners=PAGE_PARTNER_MAP.get("lumpsum_calculator", []),
    PARTNER_LINKS=PARTNER_LINKS
)
from math import pow

@app.route("/cagr_calculator", methods=["GET", "POST"])
def cagr_calculator():

    result = None

    if request.method == "POST":

        try:

            initial = float(request.form["initial"])
            final = float(request.form["final"])
            years = float(request.form["years"])

            cagr = ((final / initial) ** (1 / years) - 1) * 100

            profit = final - initial

            absolute_return = ((final - initial) / initial) * 100

            result = {
                "initial": round(initial, 2),
                "final": round(final, 2),
                "years": years,
                "profit": round(profit, 2),
                "cagr": round(cagr, 2),
                "absolute_return": round(absolute_return, 2)
            }

        except Exception as e:

            result = {
                "error": str(e)
            }

    return render_template(
        "cagr_calculator.html",
        result=result
    )
from math import pow

@app.route("/inflation_calculator", methods=["GET", "POST"])
def inflation_calculator():

    result = None

    if request.method == "POST":

        try:

            current_amount = float(request.form["current_amount"])
            inflation_rate = float(request.form["inflation_rate"])
            years = int(request.form["years"])

            future_value = current_amount * pow(
                (1 + inflation_rate / 100),
                years
            )

            purchasing_power_loss = future_value - current_amount

            yearly_data = []

            for year in range(1, years + 1):

                value = current_amount * pow(
                    (1 + inflation_rate / 100),
                    year
                )

                yearly_data.append({
                    "year": year,
                    "value": round(value, 2)
                })

            result = {

                "current_amount": round(current_amount, 2),
                "future_value": round(future_value, 2),
                "inflation_rate": inflation_rate,
                "years": years,
                "loss": round(purchasing_power_loss, 2),
                "yearly_data": yearly_data

            }

        except Exception as e:

            result = {
                "error": str(e)
            }

    return render_template(
        "inflation_calculator.html",
        result=result
    )
from datetime import datetime, timedelta

def can_generate_ai_report(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM ai_reports WHERE user_id = %s",
        (user_id,)
    )

    row = cursor.fetchone()

    # First report ever
    if not row:
        cursor.execute(
            """
            INSERT INTO ai_reports (user_id, report_count, last_generated)
            VALUES (%s, 0, NULL)
            """,
            (user_id,)
        )
        conn.commit()

        cursor.close()
        conn.close()
        return True, ""

    # Maximum 5 reports
    if row["report_count"] >= 5:
        cursor.close()
        conn.close()
        return False, "You have reached your free AI report limit."

    # One report every 24 hours
    if row["last_generated"]:
        next_time = row["last_generated"] + timedelta(hours=24)

        if datetime.now() < next_time:
            cursor.close()
            conn.close()
            return False, "Please try again after 24 hours."

    cursor.close()
    conn.close()

    return True, ""
@app.route("/generate_ai_report")
@login_required
def generate_ai_report():

    user_id = session["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor()


    # ---------------------------------------------------
    # Get logged-in user
    # ---------------------------------------------------
    cursor.execute(
        "SELECT * FROM users WHERE id=%s",
        (user_id,)
    )

    user = cursor.fetchone()


    # ---------------------------------------------------
    # Check AI report usage (1 report per 24 hours)
    # ---------------------------------------------------
    cursor.execute(
        """
        SELECT *
        FROM ai_reports
        WHERE user_id=%s
        """,
        (user_id,)
    )

    ai_record = cursor.fetchone()


    if ai_record is None:

        # First AI report generation
        cursor.execute(
            """
            INSERT INTO ai_reports
            (
                user_id,
                report_html,
                report_count,
                last_generated
            )
            VALUES
            (%s,%s,%s,NOW())
            """,
            (
                user_id,
                "Generating AI report...",
                1
            )
        )


    else:

        # ---------------------------------------------------
        # Check 24 hour limit
        # ---------------------------------------------------
        if ai_record["last_generated"]:

            elapsed = datetime.now() - ai_record["last_generated"]


            if elapsed < timedelta(hours=24):

                conn.close()

                return (
                    "You have already generated your AI report today. "
                    "Please try again after 24 hours."
                )


        # ---------------------------------------------------
        # Allow next day's report
        # ---------------------------------------------------
        cursor.execute(
            """
            UPDATE ai_reports
            SET
                report_count = 1,
                last_generated = NOW()
            WHERE user_id=%s
            """,
            (user_id,)
        )


    conn.commit()



    # ---------------------------------------------------
    # Fetch latest financial report
    # ---------------------------------------------------
    cursor.execute(
        """
        SELECT *
        FROM reports
        WHERE user_id=%s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id,)
    )


    report = cursor.fetchone()


    if not report:

        conn.close()

        return redirect(
            url_for("profile")
        )



    # ---------------------------------------------------
    # Build report data
    # ---------------------------------------------------

    savings = report["savings"]

    risk = report["risk"].lower()

    rules = RISK_RULES.get(
        risk,
        RISK_RULES["medium"]
    )


    savings_rate = (
        report["savings"] / report["income"]
    ) * 100 if report["income"] > 0 else 0


    score = int(
        40 + (savings_rate * 0.7)
    )

    score = min(score,99)



    report_data = {

        "income": report["income"],
        "expense": report["expense"],
        "savings": savings,

        "risk": risk.capitalize(),

        "sip": savings * rules["sip"],
        "large_cap": savings * rules["large_cap"],
        "mid_cap": savings * rules["mid_cap"],
        "small_cap": savings * rules["small_cap"],

        "emergency_fund": savings * rules["emergency"],

        "score": score,


        "advice": ADVISOR_INSIGHTS.get(
            risk,
            []
        ),


        # SIP Calculator
        "sip_calc_fv": 0,
        "sip_calc_monthly": 0,
        "sip_calc_years": 0,


        # Future Planning
        "future_target_amount": 0,
        "future_target_years": 0,
        "future_req_monthly": 0,


        # Retirement
        "retirement_age": 60,
        "retirement_corpus": 0,
        "retirement_monthly": 0,


        # EMI
        "emi_loan_amount": 0,
        "emi_monthly": 0,
        "emi_rate": 0,
        "emi_years": 0,
        "emi_interest": 0,
        "emi_total": 0,


        # FD
        "fd_principal": 0,
        "fd_rate": 0,
        "fd_years": 0,
        "fd_interest": 0,
        "fd_maturity": 0,


        # Tax
        "tax_income": 0,
        "tax_old": 0,
        "tax_new": 0,
        "tax_savings": 0,
        "tax_better": ""

    }



    # ---------------------------------------------------
    # Generate AI advice
    # ---------------------------------------------------

    ai_html = generate_ai_advice(report_data)


    if not ai_html:

        ai_html = """
        <p>
        AI report generation failed.
        Please try again later.
        </p>
        """



    report_data["ai_advice"] = ai_html



    # ---------------------------------------------------
    # Save AI report
    # ---------------------------------------------------

    cursor.execute(
        """
        UPDATE ai_reports
        SET
            report_html=%s
        WHERE user_id=%s
        """,
        (
            ai_html,
            user_id
        )
    )


    conn.commit()

    conn.close()



    # ---------------------------------------------------
    # Render report
    # ---------------------------------------------------

    return render_template(
        "report.html",
        user=user,
        data=report_data
    )
    # AI generation code will come in the next step
@app.route('/financial-future', methods=['GET', 'POST'])
def financial_future():

    result = None

    if request.method == 'POST':

        age = int(request.form.get('age') or 0)
        target = float(request.form.get('target') or 0)
        years = int(request.form.get('years') or 0)

        months = years * 12
        annual_return = 0.12
        monthly_rate = annual_return / 12

        if months == 0 or target == 0:

            monthly_sip = 0

        else:

            monthly_sip = target / (
                (((1 + monthly_rate) ** months - 1) / monthly_rate)
                * (1 + monthly_rate)
            )

        # -------------------------
        # Inflation
        # -------------------------

        inflation_rate = 0.06

        future_value = target * ((1 + inflation_rate) ** years)

        # -------------------------
        # Goal Difficulty
        # -------------------------

        if monthly_sip < 10000:
            difficulty = "Easy"
            badge = "🟢"

        elif monthly_sip < 30000:
            difficulty = "Moderate"
            badge = "🟡"

        else:
            difficulty = "Aggressive"
            badge = "🔴"

        # -------------------------
        # Confidence Score
        # -------------------------

        if years >= 15:
            confidence = 90

        elif years >= 10:
            confidence = 80

        elif years >= 5:
            confidence = 65

        else:
            confidence = 45

        # -------------------------
        # SmartPlan Insights
        # -------------------------

        insights = []

        insights.append(
            f"Your target of ₹{target:,.0f} could grow to approximately ₹{future_value:,.0f} after inflation."
        )

        insights.append(
            "Increasing your SIP by around 10% every year may significantly improve your long-term wealth."
        )

        insights.append(
            "Review your investment plan annually to stay aligned with your goal."
        )

        insights.append(
            "Maintain an emergency fund before increasing investment risk."
        )

        result = {

            "age": age,

            "target": "{:,.0f}".format(target),

            "future_value": "{:,.0f}".format(future_value),

            "monthly_total": "{:,.2f}".format(monthly_sip),

            "difficulty": difficulty,

            "badge": badge,

            "confidence": confidence,

            "stepup": "10%",

            "insights": insights,

            "breakdown": {

                "large": {

                    "label": "Large Cap",

                    "amount": "{:,.2f}".format(monthly_sip * 0.40),

                    "return": "10-12%"
                },

                "mid": {

                    "label": "Mid Cap",

                    "amount": "{:,.2f}".format(monthly_sip * 0.25),

                    "return": "12-14%"
                },

                "small": {

                    "label": "Small Cap",

                    "amount": "{:,.2f}".format(monthly_sip * 0.15),

                    "return": "14-16%"
                },

                "debt": {

                    "label": "Debt Funds",

                    "amount": "{:,.2f}".format(monthly_sip * 0.20),

                    "return": "7-8%"
                }
            }
        }

    return render_template(
        "financial_future.html",
        result=result,
        partners=PAGE_PARTNER_MAP.get("financial_future", []),
        PARTNER_LINKS=PARTNER_LINKS
    )
@app.route('/tax_calculator', methods=['GET', 'POST'])
def tax_calculator():

    if request.method == 'POST':

        income = float(request.form.get('income') or 0)
        investments = float(request.form.get('investments') or 0)

        # -----------------------------
        # NEW REGIME
        # -----------------------------

        std_new = 75000
        taxable_new = max(0, income - std_new)

        tax_new = 0

        slabs = [
            (400000, 0.00),
            (400000, 0.05),
            (400000, 0.10),
            (400000, 0.15),
            (400000, 0.20),
            (400000, 0.25)
        ]

        remaining = taxable_new

        for limit, rate in slabs:

            if remaining <= 0:
                break

            chunk = min(remaining, limit)
            tax_new += chunk * rate
            remaining -= chunk

        if remaining > 0:
            tax_new += remaining * 0.30

        tax_new *= 1.04

        # -----------------------------
        # OLD REGIME
        # -----------------------------

        std_old = 50000

        taxable_old = max(
            0,
            income - std_old - investments
        )

        if taxable_old <= 250000:

            tax_old = 0

        elif taxable_old <= 500000:

            tax_old = (taxable_old - 250000) * 0.05

        elif taxable_old <= 1000000:

            tax_old = 12500 + (taxable_old - 500000) * 0.20

        else:

            tax_old = 112500 + (taxable_old - 1000000) * 0.30

        tax_old *= 1.04

        # -----------------------------
        # RESULT
        # -----------------------------

        savings = abs(tax_old - tax_new)

        better_option = (
            "New Regime"
            if tax_new < tax_old
            else "Old Regime"
        )

        # -----------------------------
        # STORE IN SESSION
        # -----------------------------

        session["tax_result"] = {

    "income": income,

    "investments": investments,

    "old_regime": round(tax_old, 2),

    "new_regime": round(tax_new, 2),

    "savings": round(savings, 2),

    "better_option": better_option,

    # NEW DATA
    "taxable_old": taxable_old,

    "taxable_new": taxable_new,

    "std_old": std_old,

    "std_new": std_new,

    "monthly_old": round(tax_old / 12, 2),

    "monthly_new": round(tax_new / 12, 2),

    "monthly_saving": round(savings / 12, 2),

    "effective_old": round((tax_old / income) * 100, 2) if income else 0,

    "effective_new": round((tax_new / income) * 100, 2) if income else 0

}

        return redirect(url_for("tax_report"))

    return render_template(
        "tax_calculator.html",
        result=None,
        partners=PAGE_PARTNER_MAP.get("tax_calculator", []),
        PARTNER_LINKS=PARTNER_LINKS
    )
@app.route("/tax-report")
def tax_report():

    report = session.get("tax_result")

    if not report:
        return redirect(url_for("tax_calculator"))

    return render_template(
        "tax_report.html",
        report=report,
        partners=PAGE_PARTNER_MAP.get("tax_calculator", []),
        PARTNER_LINKS=PARTNER_LINKS
    )
@app.route("/ca-consultation", methods=["GET", "POST"])
def ca_consultation():

    if request.method == "POST":

        conn = get_db_connection()
        cur = conn.cursor()

        # PostgreSQL uses %s
        if hasattr(conn, "server_version"):

            cur.execute("""
                INSERT INTO ca_consultation_requests
                (
                    full_name,
                    mobile,
                    email,
                    city,
                    query
                )
                VALUES (%s, %s, %s, %s, %s)
            """,
            (
                request.form["full_name"],
                request.form["mobile"],
                request.form.get("email"),
                request.form.get("city"),
                request.form.get("query")
            ))

        # SQLite uses ?
        else:

            cur.execute("""
                INSERT INTO ca_consultation_requests
                (
                    full_name,
                    mobile,
                    email,
                    city,
                    query
                )
                VALUES (?, ?, ?, ?, ?)
            """,
            (
                request.form["full_name"],
                request.form["mobile"],
                request.form.get("email"),
                request.form.get("city"),
                request.form.get("query")
            ))

        conn.commit()
        conn.close()

        return render_template("ca_success.html")

    return render_template("ca_consultation.html")

    return render_template("ca_consultation.html")
@app.route("/emi_calculator", methods=["GET", "POST"])
def emi_calculator():

    result = None

    if request.method == "POST":

        loan_amount = float(request.form.get("loan_amount") or 0)
        annual_rate = float(request.form.get("interest_rate") or 0)
        tenure_years = int(request.form.get("tenure") or 0)

        monthly_rate = annual_rate / (12 * 100)
        months = tenure_years * 12

        if monthly_rate == 0:
            emi = loan_amount / months if months else 0
        else:
            emi = (
                loan_amount
                * monthly_rate
                * ((1 + monthly_rate) ** months)
            ) / (((1 + monthly_rate) ** months) - 1)

        total_payment = emi * months
        total_interest = total_payment - loan_amount

        # Save to latest report
        

        result = {
            "loan_amount": loan_amount,
            "rate": annual_rate,
            "years": tenure_years,
            "emi": emi,
            "interest": total_interest,
            "total": total_payment
        }

    return render_template(
    'emi_calculator.html',
    result=result,
    partners=PAGE_PARTNER_MAP.get('emi_calculator', []),
    PARTNER_LINKS=PARTNER_LINKS
)

@app.route("/retirement_calculator", methods=["GET", "POST"])
def retirement_calculator():

    result = None

    if request.method == "POST":

        current_age = int(request.form["current_age"])
        retirement_age = int(request.form["retirement_age"])
        monthly_expense = float(request.form["current_expense"])
        inflation = float(request.form["inflation"]) / 100
        expected_return = float(request.form["return_before"]) / 100
        return_after = float(request.form["return_after"]) / 100
        life_expectancy = int(request.form["life_expectancy"])

        years_to_retirement = retirement_age - current_age
        retirement_years = life_expectancy - retirement_age

        # Calculate inflation-adjusted monthly expense at retirement
        monthly_expense_at_retirement = (
            monthly_expense * ((1 + inflation) ** years_to_retirement)
        )

        # Calculate retirement corpus needed (25x monthly expense rule)
        retirement_corpus = (
            monthly_expense_at_retirement * 12 * 25
        )

        # Calculate monthly investment needed
        monthly_return = expected_return / 12
        months_to_retirement = years_to_retirement * 12

        if months_to_retirement == 0 or expected_return == 0:
            monthly_investment = 0
        else:
            monthly_investment = (
                retirement_corpus
                * monthly_return
                / (((1 + monthly_return) ** months_to_retirement) - 1)
            )

        # Calculate retirement readiness
        if monthly_investment < 15000:
            difficulty = "Easy"
            badge = "🟢"
            confidence = 90
        elif monthly_investment < 40000:
            difficulty = "Moderate"
            badge = "🟡"
            confidence = 75
        else:
            difficulty = "Aggressive"
            badge = "🔴"
            confidence = 55

        # Calculate sustainability score
        monthly_withdrawal = monthly_expense_at_retirement
        annual_return_on_corpus = retirement_corpus * return_after
        monthly_return_on_corpus = annual_return_on_corpus / 12
        sustainability_ratio = (monthly_return_on_corpus / monthly_withdrawal) * 100

        if sustainability_ratio >= 100:
            sustainability = "Excellent"
            sustainability_color = "green"
        elif sustainability_ratio >= 75:
            sustainability = "Good"
            sustainability_color = "orange"
        else:
            sustainability = "Needs Review"
            sustainability_color = "red"

        # Generate insights
        insights = []

        insights.append(
            f"You need a retirement corpus of ₹{retirement_corpus:,.0f} to sustain ₹{monthly_expense_at_retirement:,.0f}/month for {retirement_years} years."
        )

        insights.append(
            f"At ₹{monthly_investment:,.0f}/month investment, you can accumulate the required corpus in {years_to_retirement} years."
        )

        if sustainability_ratio >= 100:
            insights.append(
                f"Your portfolio returns (₹{monthly_return_on_corpus:,.0f}/month) can sustain your retirement lifestyle. You're on track!"
            )
        else:
            shortfall = monthly_withdrawal - monthly_return_on_corpus
            insights.append(
                f"You'll have a monthly shortfall of ₹{shortfall:,.0f}. Consider increasing corpus or reducing expenses."
            )

        insights.append(
            "Review your plan annually and adjust for inflation, life changes, and market conditions."
        )

        result = {
            "corpus": "{:,.0f}".format(retirement_corpus),
            "monthly_investment": "{:,.0f}".format(monthly_investment),
            "monthly_expense_today": "{:,.0f}".format(monthly_expense),
            "monthly_expense_retirement": "{:,.0f}".format(monthly_expense_at_retirement),
            "current_age": current_age,
            "retirement_age": retirement_age,
            "years_to_retirement": years_to_retirement,
            "retirement_years": retirement_years,
            "life_expectancy": life_expectancy,
            "inflation": f"{inflation * 100:.1f}%",
            "return_before": f"{expected_return * 100:.1f}%",
            "return_after": f"{return_after * 100:.1f}%",
            "difficulty": difficulty,
            "badge": badge,
            "confidence": confidence,
            "sustainability": sustainability,
            "sustainability_color": sustainability_color,
            "sustainability_ratio": f"{sustainability_ratio:.0f}%",
            "monthly_return_on_corpus": "{:,.0f}".format(monthly_return_on_corpus),
            "insights": insights,
        }

    return render_template(
        'retirement_calculator.html',
        result=result,
        partners=PAGE_PARTNER_MAP.get('retirement_calculator', []),
        PARTNER_LINKS=PARTNER_LINKS
    )

    
@app.route("/fd_calculator", methods=["GET", "POST"])
def fd_calculator():

    result = None

    if request.method == "POST":

        try:
            principal = float(request.form.get("principal") or 0)
            rate = float(request.form.get("rate") or 0)
            years = float(request.form.get("years") or 0)

            # Quarterly Compounding
            r = rate / 100
            n = 4

            maturity_amount = principal * ((1 + (r / n)) ** (n * years))
            interest_earned = maturity_amount - principal

            # Additional SmartPlan Metrics
            total_return_percent = (
                (interest_earned / principal) * 100
                if principal else 0
            )

            average_monthly_growth = (
                interest_earned / (years * 12)
                if years else 0
            )

            effective_annual_yield = (
                ((1 + (r / n)) ** n - 1) * 100
            )

            # Simple Investment Rating
            if total_return_percent >= 80:
                rating = "⭐⭐⭐⭐⭐ Excellent Growth"
            elif total_return_percent >= 50:
                rating = "⭐⭐⭐⭐ Very Good"
            elif total_return_percent >= 25:
                rating = "⭐⭐⭐ Moderate"
            else:
                rating = "⭐⭐ Stable & Conservative"

            # SmartPlan AI Insight
            if years <= 3:
                insight = (
                    "This FD is suitable for short-term goals such as emergency funds "
                    "or planned purchases. It offers stability with low risk."
                )

            elif years <= 7:
                insight = (
                    "This investment duration is ideal for medium-term goals. "
                    "Compare FD rates across banks before investing to maximize returns."
                )

            else:
                insight = (
                    "For long-term wealth creation, Fixed Deposits provide safety, "
                    "but consider combining them with equity mutual funds to help "
                    "beat inflation over longer periods."
                )

            # Return Data
            result = {
                "principal": principal,
                "rate": rate,
                "years": years,
                "interest": interest_earned,
                "maturity": maturity_amount,
                "return_percent": round(total_return_percent, 2),
                "monthly_growth": average_monthly_growth,
                "effective_yield": round(effective_annual_yield, 2),
                "rating": rating,
                "insight": insight
            }

        except ValueError:
            result = None

    return render_template(
        "fd_calculator.html",
        result=result,
        partners=PAGE_PARTNER_MAP.get("fd_calculator", []),
        PARTNER_LINKS=PARTNER_LINKS
    )
"""
Route + calculation logic for the In-Hand Salary Calculator.
Paste this into your main Flask app file (same place as loan_eligibility_calculator,
emi_calculator, networth_calculator, etc).

URL:  /in-hand-salary-calculator
Template:  in_hand_salary_calculator.html  (put in your templates/ folder)

Tax data used (FY 2025-26 / AY 2026-27, unchanged for FY 2026-27 per Budget 2026):
- New regime slabs: 0-4L nil, 4-8L 5%, 8-12L 10%, 12-16L 15%, 16-20L 20%,
  20-24L 25%, above 24L 30%. Standard deduction Rs.75,000. Sec 87A rebate up to
  Rs.60,000 (net tax nil for taxable income <= Rs.12L), with marginal relief just above.
- Old regime slabs (age-based): below 60 -> 2.5L/5L/10L; 60-80 -> 3L/5L/10L;
  above 80 -> 5L/10L. Standard deduction Rs.50,000. Sec 87A rebate up to Rs.12,500
  (net tax nil for taxable income <= Rs.5L).
- 4% Health & Education Cess on tax (after surcharge) under both regimes.
- Simplified surcharge: >50L 10%, >1Cr 15%, >2Cr 25% (both regimes); old regime
  additionally 37% above 5Cr (new regime surcharge is capped at 25%).
This is a planning estimate, not a substitute for a CA / Form 16 computation.
"""

NEW_REGIME_SLABS = [
    (0, 400000, 0),
    (400000, 800000, 5),
    (800000, 1200000, 10),
    (1200000, 1600000, 15),
    (1600000, 2000000, 20),
    (2000000, 2400000, 25),
    (2400000, float('inf'), 30),
]

OLD_REGIME_SLABS = {
    'below60': [(0, 250000, 0), (250000, 500000, 5), (500000, 1000000, 20), (1000000, float('inf'), 30)],
    '60to80': [(0, 300000, 0), (300000, 500000, 5), (500000, 1000000, 20), (1000000, float('inf'), 30)],
    'above80': [(0, 500000, 0), (500000, 1000000, 20), (1000000, float('inf'), 30)],
}


def _slab_tax(taxable, slabs):
    tax = 0
    for lower, upper, rate in slabs:
        if taxable > lower:
            tax += (min(taxable, upper) - lower) * rate / 100
        else:
            break
    return tax


def _surcharge_rate(taxable, regime):
    if taxable > 20000000:
        return 0.37 if regime == 'old' else 0.25
    elif taxable > 10000000:
        return 0.15
    elif taxable > 5000000:
        return 0.10
    return 0


def compute_new_regime_tax(taxable):
    if taxable <= 1200000:
        return 0.0
    tax = _slab_tax(taxable, NEW_REGIME_SLABS)
    # Marginal relief just above the 12L rebate threshold
    excess = taxable - 1200000
    if tax > excess:
        tax = excess
    surcharge = tax * _surcharge_rate(taxable, 'new')
    return round((tax + surcharge) * 1.04, 2)


def compute_old_regime_tax(taxable, age_group):
    slabs = OLD_REGIME_SLABS.get(age_group, OLD_REGIME_SLABS['below60'])
    if taxable <= 500000:
        return 0.0
    tax = _slab_tax(taxable, slabs)
    surcharge = tax * _surcharge_rate(taxable, 'old')
    return round((tax + surcharge) * 1.04, 2)


@app.route('/in-hand-salary-calculator', methods=['GET', 'POST'])
def in_hand_salary_calculator():
    """
    In-Hand Salary Calculator
    Converts Annual CTC into monthly take-home pay, showing the PF/gratuity
    held back, income tax under both regimes, and which regime saves more.
    """
    result = None

    if request.method == 'POST':
        try:
            annual_ctc = float(request.form.get('annual_ctc', 0))
            basic_percent = float(request.form.get('basic_percent', 40))
            metro_city = request.form.get('metro_city', 'yes') == 'yes'
            monthly_rent_paid = float(request.form.get('monthly_rent_paid', 0) or 0)
            tax_regime = request.form.get('tax_regime', 'new')
            age_group = request.form.get('age_group', 'below60')
            professional_tax_annual = float(request.form.get('professional_tax_annual', 2400) or 0)
            other_deductions = float(request.form.get('other_deductions', 0) or 0)

            if annual_ctc <= 0:
                raise ValueError("Annual CTC must be greater than 0")
            if basic_percent < 20 or basic_percent > 60:
                raise ValueError("Basic salary percentage should be between 20% and 60%")

            # --- Salary structure breakup ---
            basic = annual_ctc * basic_percent / 100
            hra_pct = 0.50 if metro_city else 0.40
            hra_received = basic * hra_pct

            employer_pf = basic * 0.12
            gratuity = basic * 0.0481
            retirals = employer_pf + gratuity

            gross_salary = max(0, annual_ctc - retirals)
            special_allowance = max(0, gross_salary - basic - hra_received)
            employee_pf = basic * 0.12

            def taxable_and_tax(regime):
                if regime == 'new':
                    taxable = max(0, gross_salary - 75000)
                    tax = compute_new_regime_tax(taxable)
                    hra_exempt = 0
                    sec80c = 0
                else:
                    hra_exempt = 0
                    if monthly_rent_paid > 0:
                        annual_rent = monthly_rent_paid * 12
                        excess_rent = max(0, annual_rent - basic * 0.10)
                        hra_exempt = min(hra_received, excess_rent, basic * hra_pct)
                    sec80c = min(employee_pf, 150000)
                    taxable = max(0, gross_salary - hra_exempt - 50000 - sec80c - other_deductions)
                    tax = compute_old_regime_tax(taxable, age_group)
                return taxable, tax, hra_exempt, sec80c

            new_taxable, new_tax, _, _ = taxable_and_tax('new')
            old_taxable, old_tax, old_hra_exempt, old_sec80c = taxable_and_tax('old')

            if tax_regime == 'new':
                income_tax = new_tax
                taxable_income = new_taxable
            else:
                income_tax = old_tax
                taxable_income = old_taxable

            total_deductions = employee_pf + professional_tax_annual + income_tax
            annual_take_home = max(0, gross_salary - total_deductions)
            monthly_take_home = annual_take_home / 12
            in_hand_percent = (annual_take_home / annual_ctc) * 100 if annual_ctc > 0 else 0
            effective_tax_rate = (income_tax / gross_salary * 100) if gross_salary > 0 else 0

            better_regime = 'New Regime' if new_tax <= old_tax else 'Old Regime'
            tax_saving_by_switching = abs(new_tax - old_tax)

            insights = []

            if better_regime.lower().startswith(tax_regime):
                insights.append("✓ You've selected the {} for this calculation, which also comes out cheaper for your numbers — Old Regime tax: ₹{:,.0f}, New Regime tax: ₹{:,.0f}.".format(
                    'New Regime' if tax_regime == 'new' else 'Old Regime', old_tax, new_tax))
            else:
                insights.append("⚠ The {} looks cheaper for your inputs — you could save about ₹{:,.0f}/year in tax by switching (Old: ₹{:,.0f} vs New: ₹{:,.0f}).".format(
                    better_regime, tax_saving_by_switching, old_tax, new_tax))

            insights.append("ℹ ₹{:,.0f} of your CTC (Employer PF + Gratuity) is held back for retirement/exit and isn't part of your monthly in-hand pay.".format(retirals))

            if tax_regime == 'old':
                if old_hra_exempt > 0:
                    insights.append("✓ You're claiming ₹{:,.0f} in HRA exemption and ₹{:,.0f} under Section 80C, lowering your taxable income.".format(old_hra_exempt, old_sec80c))
                else:
                    insights.append("⚠ No HRA exemption applied — add your monthly rent paid if you live in rented accommodation to reduce taxable income.")
            else:
                insights.append("ℹ The New Regime doesn't allow HRA or 80C exemptions, but it has lower slab rates and a bigger rebate — often a wash or better for those without large deductions.")

            if in_hand_percent < 65:
                insights.append("⚠ Your in-hand pay is about {:.0f}% of CTC. A high basic salary % and PF/gratuity structuring account for most of the gap.".format(in_hand_percent))
            else:
                insights.append("✓ You're taking home about {:.0f}% of your CTC every year, which is a healthy in-hand ratio.".format(in_hand_percent))

            result = {
                'annual_ctc': f"{annual_ctc:,.0f}",
                'basic': f"{basic:,.0f}",
                'hra_received': f"{hra_received:,.0f}",
                'special_allowance': f"{special_allowance:,.0f}",
                'employer_pf': f"{employer_pf:,.0f}",
                'gratuity': f"{gratuity:,.0f}",
                'retirals': f"{retirals:,.0f}",
                'gross_salary': f"{gross_salary:,.0f}",
                'employee_pf': f"{employee_pf:,.0f}",
                'professional_tax_annual': f"{professional_tax_annual:,.0f}",
                'taxable_income': f"{taxable_income:,.0f}",
                'income_tax': f"{income_tax:,.0f}",
                'effective_tax_rate': f"{effective_tax_rate:.1f}",
                'total_deductions': f"{total_deductions:,.0f}",
                'annual_take_home': f"{annual_take_home:,.0f}",
                'monthly_take_home': f"{monthly_take_home:,.0f}",
                'in_hand_percent': f"{in_hand_percent:.1f}",
                'in_hand_percent_value': in_hand_percent,
                'tax_regime': 'New Regime' if tax_regime == 'new' else 'Old Regime',
                'new_regime_tax': f"{new_tax:,.0f}",
                'old_regime_tax': f"{old_tax:,.0f}",
                'better_regime': better_regime,
                'tax_saving_by_switching': f"{tax_saving_by_switching:,.0f}",
                'regime_matches_best': better_regime.lower().startswith(tax_regime),
                'insights': insights,
                'confidence': 80,
            }

        except Exception as e:
            result = {'error': str(e)}

    return render_template(
        'in_hand_salary_calculator.html',
        result=result,
        partners=PAGE_PARTNER_MAP.get("in_hand_salary_calculator", []),
        PARTNER_LINKS=PARTNER_LINKS
    )
@app.route("/handbook")
def handbook():
    return render_template("handbook.html")
@app.route('/admin')
@requires_auth
def admin():

    conn = get_db_connection()
    cur = conn.cursor()

    # ---------------- Reports ----------------

    query = """
        SELECT
            r.id,
            u.name,
            u.mobile,
            u.country,
            r.income,
            r.expense,
            r.savings,
            r.risk,
            r.created_at,
            u.target_amount,
            u.target_years
        FROM reports r
        INNER JOIN users u
        ON r.user_id = u.id
        ORDER BY r.id DESC
    """

    cur.execute(query)

    rows = cur.fetchall()
    

    cleaned_reports = []

    for r_dict in rows:

       

        if (
        r_dict.get("name") and r_dict["name"].replace("-", "").replace(".", "").isdigit()
        ):


            r_dict["name"] = f"User #{r_dict['id']}"

        cleaned_reports.append(r_dict)

    total_reports = len(cleaned_reports)

    high_risk = sum(
        1 for r in cleaned_reports
        if r['risk'].lower() == 'high'
    )

    medium_risk = sum(
        1 for r in cleaned_reports
        if r['risk'].lower() == 'medium'
    )

    low_risk = sum(
        1 for r in cleaned_reports
        if r['risk'].lower() == 'low'
    )

    avg_income = (
        sum(r['income'] for r in cleaned_reports) / total_reports
        if total_reports > 0 else 0
    )

    avg_savings = (
        sum(r['savings'] for r in cleaned_reports) / total_reports
        if total_reports > 0 else 0
    )

    # ---------------- Loan Leads ----------------

    cur.execute("""
        SELECT *
        FROM loan_leads
        ORDER BY created_at DESC
    """)

    loan_leads = cur.fetchall()

    total_loan_leads = len(loan_leads)

    # ---------------- Tax Leads ----------------

    cur.execute("""
        SELECT *
        FROM tax_leads
        ORDER BY created_at DESC
    """)

    tax_leads = cur.fetchall()

    total_tax_leads = len(tax_leads)

    # ---------------- CA Consultation Requests ----------------

    cur.execute("""
        SELECT *
        FROM ca_consultation_requests
        ORDER BY created_at DESC
    """)

    ca_requests = cur.fetchall()

    total_ca_requests = len(ca_requests)

    conn.close()

    return render_template(

        "admin.html",

        total_reports=total_reports,

        high_risk=high_risk,

        medium_risk=medium_risk,

        low_risk=low_risk,

        avg_income="{:,.2f}".format(avg_income),

        avg_savings="{:,.2f}".format(avg_savings),

        reports=cleaned_reports,

        loan_leads=loan_leads,

        total_loan_leads=total_loan_leads,

        tax_leads=tax_leads,

        total_tax_leads=total_tax_leads,

        ca_requests=ca_requests,

        total_ca_requests=total_ca_requests

    )
@app.route('/articles')
def articles():
    return get_cached_articles_html()

@app.route('/blog/<slug>')
def view_article(slug):
    html = get_cached_article_page(slug)
    if html is None:
        return "Article not found", 404
    return html

    current_text = (
        article["title"]
        + " "
        + article["content"]
    ).lower()


    keywords = [
        "sip",
        "investment",
        "mutual fund",
        "salary",
        "saving",
        "tax",
        "retirement",
        "fd",
        "financial",
        "wealth",
        "emergency fund",
        "budget"
    ]


    matched_keywords = []


    for word in keywords:

        if word in current_text:
            matched_keywords.append(word)



    if matched_keywords:


        conditions = " OR ".join(
            [
                "LOWER(title) LIKE %s",
                "LOWER(content) LIKE %s"
            ]
        )


        query = """
        SELECT id,title,slug
        FROM articles
        WHERE slug != %s
        AND (
        """


        params = [slug]


        search_parts = []


        for word in matched_keywords:

            search_parts.append(
                "LOWER(title) LIKE %s OR LOWER(content) LIKE %s"
            )

            params.extend(
                [
                    f"%{word}%",
                    f"%{word}%"
                ]
            )


        query += " OR ".join(search_parts)

        query += """
        )
        ORDER BY created_at DESC
        LIMIT 5
        """


        cur.execute(
            query,
            params
        )


        related_articles = cur.fetchall()


    else:

        cur.execute(
            """
            SELECT id,title,slug
            FROM articles
            WHERE slug != %s
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (slug,)
        )


        related_articles = cur.fetchall()



    conn.close()
    is_admin = False
    auth = request.authorization
    if auth and check_auth(auth.username, auth.password):
        is_admin = True
    
    return render_template(
        'view_article.html',
        article=article,
        related_articles=related_articles,

is_admin=is_admin
    )

@app.route("/disclaimer")
def disclaimer():
    return render_template("disclaimer.html")
@app.route("/about")
def about():
    return render_template("about.html")
@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route('/generate-faq-pdf')
def generate_faq():
    # Trigger the generation function
    FAQ.create_faq_pdf()
    
    # After it's created, send it to the user's browser
    return send_file('financial_guide.pdf', as_attachment=True)
@app.route('/wellness', methods=['GET', 'POST'])
def wellness_health():

    if request.method == 'POST':

        income = float(request.form.get('income') or 0)
        expense = float(request.form.get('expense') or 0)
        savings = float(request.form.get('savings') or 0)
        emergency_fund = float(request.form.get('emergency_fund') or 0)
        debt = float(request.form.get('debt') or 0)

        # Store in session temporarily (no login needed, no DB write yet)
        session['wellness_health'] = {
            "income": income,
            "expense": expense,
            "savings": savings,
            "emergency_fund": emergency_fund,
            "debt": debt
        }

        return redirect(url_for('wellness_quiz'))

    return render_template('wellness_health.html')


@app.route('/wellness/quiz', methods=['GET', 'POST'])
def wellness_quiz():

    if 'wellness_health' not in session:
        return redirect(url_for('wellness_health'))

    if request.method == 'POST':

        answers = {}
        for q in LITERACY_QUESTIONS:
            answers[q['id']] = request.form.get(q['id'])

        correct_count, total = calculate_literacy_score(answers)

        session['wellness_literacy'] = {
            "correct": correct_count,
            "total": total
        }

        return redirect(url_for('wellness_results'))

    return render_template('wellness_quiz.html', questions=LITERACY_QUESTIONS)


@app.route('/wellness/results')
def wellness_results():

    health_data = session.get('wellness_health')
    literacy_data = session.get('wellness_literacy')

    if not health_data or not literacy_data:
        return redirect(url_for('wellness_health'))

    health_score = calculate_health_score(
        health_data['income'],
        health_data['expense'],
        health_data['savings'],
        health_data['emergency_fund'],
        health_data['debt']
    )

    breakdown_notes = get_health_breakdown(
        health_data['income'],
        health_data['expense'],
        health_data['savings'],
        health_data['emergency_fund'],
        health_data['debt']
    )

    literacy_score = literacy_data['correct']
    literacy_total = literacy_data['total']

    # Save anonymous result to DB
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO wellness_results (health_score, literacy_score, literacy_total)
        VALUES (%s, %s, %s)
    """, (health_score, literacy_score, literacy_total))
    conn.commit()
    conn.close()

    # Generate AI-personalized summary
    ai_summary = generate_wellness_summary(health_score, literacy_score, literacy_total, breakdown_notes)

    # Clear session data now that we're done with it
    session.pop('wellness_health', None)
    session.pop('wellness_literacy', None)

    return render_template(
        'wellness_results.html',
        health_score=health_score,
        literacy_score=literacy_score,
        literacy_total=literacy_total,
        ai_summary=ai_summary
    )
@app.route("/health")
def health():
    return {
        "status": "healthy",
        "application": "SmartPlan Finance",
        "version": "2.1"
    }, 200

from flask import send_from_directory

@app.route("/ads.txt")
def ads_txt():
    return send_from_directory("static", "ads.txt", mimetype="text/plain")

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

    # =========================
    # PUBLIC PLATFORM PAGES
    # =========================

    static_urls = [
        ("https://smartplanfinance.com/", "daily", "1.0"),
        ("https://smartplanfinance.com/articles", "daily", "0.9"),
        ("https://smartplanfinance.com/books", "weekly", "0.8"),
        ("https://smartplanfinance.com/handbook", "monthly", "0.8"),
        ("https://smartplanfinance.com/wellness", "monthly", "0.8"),
        ("https://smartplanfinance.com/financial-planner", "monthly", "0.9"),

        # Calculators
        ("https://smartplanfinance.com/cagr_calculator", "monthly", "0.8"),
        ("https://smartplanfinance.com/emi_calculator", "monthly", "0.8"),
        ("https://smartplanfinance.com/fd_calculator", "monthly", "0.8"),
        ("https://smartplanfinance.com/in-hand-salary-calculator", "monthly", "0.8"),
        ("https://smartplanfinance.com/inflation_calculator", "monthly", "0.8"),
        ("https://smartplanfinance.com/loan-eligibility-calculator", "monthly", "0.8"),
        ("https://smartplanfinance.com/lumpsum_calculator", "monthly", "0.8"),
        ("https://smartplanfinance.com/networth-calculator", "monthly", "0.8"),
        ("https://smartplanfinance.com/retirement_calculator", "monthly", "0.8"),
        ("https://smartplanfinance.com/sip-calculator", "monthly", "0.8"),
        ("https://smartplanfinance.com/swp_calculator", "monthly", "0.8"),
        ("https://smartplanfinance.com/tax_calculator", "monthly", "0.8"),
        ("https://smartplanfinance.com/xirr-calculator", "monthly", "0.8"),
    ]

    for url, changefreq, priority in static_urls:
        xml.append(f"""
    <url>
        <loc>{url}</loc>
        <changefreq>{changefreq}</changefreq>
        <priority>{priority}</priority>
    </url>
    """)

    # =========================
    # ALL BLOG ARTICLES
    # =========================

    for article in articles:
        slug = article["slug"]
        created_at = str(article["created_at"]).split(" ")[0]

        xml.append(f"""
    <url>
        <loc>https://smartplanfinance.com/blog/{slug}</loc>
        <lastmod>{created_at}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.8</priority>
    </url>
    """)

    xml.append("</urlset>")

    return Response("\n".join(xml), mimetype="application/xml")
@app.route("/city-wise-income-calculator", methods=["GET", "POST"])
def city_income_calculator():

    result = None
    error = None

    city = ""
    household = ""
    housing = ""
    lifestyle = ""
    children = ""

    if request.method == "POST":

        city = request.form.get("city", "").strip()
        household = request.form.get("household", "").strip()
        housing = request.form.get("housing", "").strip()
        lifestyle = request.form.get("lifestyle", "").strip()
        children = request.form.get("children", "").strip()

        try:
            # The calculator calculations are handled by the HTML/JavaScript.
            # This route simply serves the calculator page.

            result = True

        except Exception as e:
            print("City Income Calculator Error:", e)
            error = "Unable to process the calculator request."

    return render_template(
        "city_income_calculator.html",
        result=result,
        error=error,
        city=city,
        household=household,
        housing=housing,
        lifestyle=lifestyle,
        children=children
    )
@app.route("/stock-analyzer", methods=["GET", "POST"])
def stock_analyzer():

    stock = None
    ai_report = None
    error = None

    age = ""
    risk = ""
    years = ""

    if request.method == "POST":

        symbol = request.form.get("symbol", "").strip()
        age = request.form.get("age", "").strip()
        risk = request.form.get("risk_appetite", "").strip()
        years = request.form.get("investment_years", "").strip()

        if symbol:

            print("="*60)
            print("Searching for:", symbol)

            stock = get_stock_data(symbol)
            session["stock_data"] = stock
            session["age"] = age
            session["risk"] = risk
            session["years"] = years
            print("Result:", stock)

            if stock:

                print("Generating AI Report...")

                ai_report = generate_stock_analysis(
                    stock,
                    age,
                    risk,
                    years
                )

                print("AI Report Generated Successfully.")

            else:

                error = "Unable to fetch stock information."

    return render_template(

        "stock_analyzer.html",

        stock=stock,

        ai_report=None,

        error=error,

        age=age,

        risk=risk,

        years=years
        
    )

@app.route("/generate-stock-advice", methods=["POST"])
def generate_stock_advice():

    print("Generating SPF Advice...")

    symbol = request.form.get("symbol")
    age = request.form.get("age")
    risk = request.form.get("risk_appetite")
    years = request.form.get("investment_years")


    stock = get_stock_data(symbol)


    if stock is None:
        return redirect(url_for("stock_analyzer"))


    ai_report = generate_stock_analysis(
        stock,
        age,
        risk,
        years
    )


    print("SPF Advice Generated Successfully")


    return render_template(
        "stock_analyzer.html",
        stock=stock,
        ai_report=ai_report,
        age=age,
        risk=risk,
        years=years,
        error=None
    )
# ============================================================================
# BOOK METADATA & CONFIGURATION
# ============================================================================
# Add this section right after your imports and before the app initialization

BOOKS_CATALOG = {
    "book1": {
        "id": "book1",
        "title": "Smart Plan Finance",
        "subtitle": "Master Your Money. Build Your Wealth.",
        "description": "A practical guide to building wealth, managing money, and achieving financial freedom — 450+ pages covering budgeting, investing, tax planning, and retirement.",
        "author": "Argho Sanyal",
        "price": 29900,  # in paise for Razorpay
        "price_display": "₹299",
        "cover": "SmartPlanFinanceCover.png",
        "preview_file": "SmartPlanFinance.pdf",
        "full_file": "SmartPlanFinance.pdf",
        "preview_pages": 50,
        "preview_type": "limited",
        "pages": "450+",
    },
    "book2": {
        "id": "book2",
        "title": "Smart Plan Finance — From First Salary to Financial Freedom",
        "subtitle": "A Practical Money Guide for Young Professionals",
        "description": "A practical money guide for young professionals from your first salary to financial freedom.",
        "author": "Argho Sanyal",
        "price": 9900,  # in paise for Razorpay
        "price_display": "₹99",
        "cover": "SmartPlanFinanceBook2.png",
        "preview_file": "Final_SmartPlanFinance_Professional.pdf",
        "full_file": "Final_SmartPlanFinance_Professional.pdf",
        "preview_pages": None,  # None means full book
        "preview_type": "full",
        "pages": "Full Book",
    }
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_book(book_id):
    """Safely retrieve book metadata"""
    return BOOKS_CATALOG.get(book_id)


def validate_book_id(book_id):
    """Check if book_id is valid"""
    return book_id in BOOKS_CATALOG


def book_purchase_required(f):
    """Decorator to check if user has purchased a book"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('book_paid'):
            return redirect(url_for('books'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# PUBLIC ROUTES - BOOK PAGES
# ============================================================================


@app.route('/books')
def books():
    """Display all available books"""
    return render_template('books.html', books=BOOKS_CATALOG)


@app.route('/spf/book')
def book_1():
    """Book 1 - SmartPlanFinance purchase links"""
    return redirect(
        "https://amzn.in/d/01T2AhP3"
    )


@app.route('/spf/book2')
def book_2():
    """Book 2 - SmartPlanFinance: From First Salary to Financial Freedom"""
    return redirect(
        "https://amzn.in/d/0hWGDW2B-"
    )

@app.route('/spf/book-preview')
def book_1_preview():
    """Book 1 preview (first 50 pages)"""
    return render_template('preview.html', book='book1')


@app.route('/spf/book2-preview')
def book_2_preview():
    """Book 2 preview (full book)"""
    return render_template('preview.html', book='book2')


# ============================================================================
# PAYMENT ROUTES - CHECKOUT & PAYMENT
# ============================================================================








# ============================================================================
# INFORMATION PAGES
# ============================================================================



# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(400)
def bad_request(e):
    """Handle 400 Bad Request"""
    app.logger.error(f"Bad Request: {str(e)}")
    return render_template('error.html', 
                         error='Bad Request', 
                         message='The request could not be understood by the server.'), 400


@app.errorhandler(403)
def forbidden(e):
    """Handle 403 Forbidden"""
    app.logger.error(f"Forbidden: {str(e)}")
    return render_template('error.html', 
                         error='Forbidden', 
                         message='You do not have permission to access this resource.'), 403


@app.errorhandler(404)
def not_found(e):
    """Handle 404 Not Found"""
    return render_template('error.html', 
                         error='Not Found', 
                         message='The page you are looking for does not exist.'), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 Internal Server Error"""
    app.logger.error(f"Internal Server Error: {str(e)}")
    return render_template('error.html', 
                         error='Server Error', 
                         message='An internal server error occurred. Please try again later.'), 500


# ============================================================================
# LOGGING & MIDDLEWARE
# ============================================================================

@app.before_request
def log_request():
    """Log incoming requests"""
    app.logger.info(f"{request.method} {request.path} - {request.remote_addr}")


def _inject_default_seo_meta(response):
    # Article templates already include complete, page-specific SEO metadata.
    # Skipping a full HTML scan here keeps cached article responses lightweight.
    if request.endpoint in {"articles", "view_article"}:
        return response

    if not response.content_type or 'text/html' not in response.content_type.lower():
        return response

    try:
        html = response.get_data(as_text=True)
    except Exception:
        return response

    if '<head' not in html.lower() or '</head>' not in html.lower():
        return response

    insert_pos = html.lower().rfind('</head>')
    if insert_pos == -1:
        return response

    tags = []
    if 'rel="canonical"' not in html and "rel='canonical'" not in html:
        tags.append(f'<link rel="canonical" href="{SITE_URL}{request.path}" />')
    if 'name="description"' not in html and "name='description'" not in html:
        tags.append(f'<meta name="description" content="{DEFAULT_SEO_DESCRIPTION}" />')
    if 'property="og:title"' not in html and "property='og:title'" not in html:
        page_title = ''
        start = html.lower().find('<title>')
        end = html.lower().find('</title>')
        if start != -1 and end != -1:
            page_title = html[start + 7:end].strip()
        tags.append(f'<meta property="og:title" content="{page_title or "SmartPlan Finance"}" />')
    if 'property="og:description"' not in html and "property='og:description'" not in html:
        tags.append(f'<meta property="og:description" content="{DEFAULT_SEO_DESCRIPTION}" />')
    if 'property="og:url"' not in html and "property='og:url'" not in html:
        tags.append(f'<meta property="og:url" content="{SITE_URL}{request.path}" />')
    if 'property="og:image"' not in html and "property='og:image'" not in html:
        tags.append(f'<meta property="og:image" content="{SITE_URL}/static/images/logo.png" />')
    if 'name="twitter:card"' not in html and "name='twitter:card'" not in html:
        tags.append('<meta name="twitter:card" content="summary_large_image" />')
    if 'name="robots"' not in html and "name='robots'" not in html:
        tags.append('<meta name="robots" content="index, follow" />')

    if tags:
        html = html[:insert_pos] + '\n' + '\n'.join(tags) + '\n' + html[insert_pos:]
        response.set_data(html)
    return response


@app.after_request
def log_response(response):
    response = _inject_default_seo_meta(response)

    # Public article pages do not vary by visitor. Short browser caching makes
    # repeat visits instant, while shared caches can reuse the rendered HTML.
    if request.method == "GET" and request.endpoint in {"articles", "view_article"}:
        response.cache_control.public = True
        response.cache_control.max_age = 300
        response.cache_control.s_maxage = 900

    app.logger.info(f"Response: {response.status_code}")
    return response


# ============================================================================
# CONTEXT PROCESSORS
# ============================================================================

@app.context_processor
def inject_books():
    """Make books available in all templates"""
    return dict(BOOKS_CATALOG=BOOKS_CATALOG)


@app.context_processor
def inject_site_config():
    """Make site configuration available in all templates"""
    return dict(
        site_name='SmartPlan Finance',
        site_url='https://smartplanfinance.com',
        author='Argho Sanyal'
    )


# ============================================================================
# COMMAND LINE INTERFACE (OPTIONAL)
# ============================================================================

@app.shell_context_processor
def make_shell_context():
    """Create context for Flask shell"""
    return {
        'db': get_db_connection,
        'BOOKS_CATALOG': BOOKS_CATALOG,
        'get_book': get_book,
        'validate_book_id': validate_book_id
    }


# ============================================================================
# API ENDPOINTS (OPTIONAL - FOR DASHBOARD/ANALYTICS)
# ============================================================================

@app.route('/api/sales-summary')
def api_sales_summary():
    """Get sales summary by book (protected endpoint)"""
    try:
        # Add authentication check here if needed
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                book_id, 
                book_name, 
                COUNT(*) as total_sales,
                SUM(amount) as total_revenue,
                AVG(amount) as avg_price
            FROM book_orders
            WHERE payment_status = 'SUCCESS'
            GROUP BY book_id, book_name
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        summary = []
        for row in results:
            summary.append({
                'book_id': row[0],
                'book_name': row[1],
                'total_sales': row[2],
                'total_revenue': float(row[3]) if row[3] else 0,
                'avg_price': float(row[4]) if row[4] else 0
            })
        
        return jsonify(summary), 200
    
    except Exception as e:
        app.logger.error(f"API Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/orders/<book_id>')
def api_orders(book_id):
    """Get orders for a specific book"""
    try:
        # Add authentication check here if needed
        if not validate_book_id(book_id):
            return jsonify({'error': 'Invalid book ID'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT order_number, customer_name, customer_email, amount, created_at
            FROM book_orders
            WHERE book_id = %s AND payment_status = 'SUCCESS'
            ORDER BY created_at DESC
            LIMIT 100
        """, (book_id,))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        orders = []
        for row in results:
            orders.append({
                'order_number': row[0],
                'customer_name': row[1],
                'customer_email': row[2],
                'amount': float(row[3]),
                'date': row[4].isoformat() if row[4] else None
            })
        
        return jsonify(orders), 200
    
    except Exception as e:
        app.logger.error(f"API Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================




# ============================================================================
#

# =====================================================================
# REPLACE your existing `financial_planner` view function with this one.
# Do NOT touch `financial_plan_results` or `download_financial_pdf` —
# they are untouched and already correct.
#
# WHAT CHANGED AND WHY
# ---------------------------------------------------------------------
# Your old JS did: stepInput.value = currentStep + 1  (on Next)
#                   stepInput.value = currentStep - 1  (on Back)
# ...and then submitted the CURRENT step's form fields under that
# wrong step number. Your backend uses `step` to decide which fields
# to parse — so it was always parsing the WRONG step's fields, and
# every step's real data was silently thrown away. By "Generate My
# Plan" the session data was basically empty, which threw inside
# financial_plan_results() and bounced you back to Step 1.
#
# THE FIX: the template now always submits `step` = the step CURRENTLY
# on screen (unchanged — it never increments/decrements client-side),
# plus a new hidden `action` field ("next" or "back"). This route:
#   - action == "next" (default): parses+validates the fields for
#     `step` exactly as before, saves them, then advances to step+1.
#   - action == "back": does NOT touch/parse/validate anything —
#     it just renders step-1 using whatever is already in the session.
# =====================================================================



@app.route('/financial-planner', methods=['GET', 'POST'])
def financial_planner():
    """
    PRODUCTION-READY Personal Financial Planning Engine
    Complete multi-step wizard with proper validation and data flow
    """

    if request.method == 'POST':
        step = request.form.get('step', '1')
        action = request.form.get('action', 'next')

        # Initialize session data if not exists
        if 'financial_plan' not in session:
            session['financial_plan'] = {}

        plan_data = session['financial_plan']

        # -----------------------------------------------------------
        # BACK NAVIGATION — never parse or validate fields going back.
        # Just show the previous step with whatever is already saved.
        # -----------------------------------------------------------
        if action == 'back':
            try:
                target_step = int(step) - 1
            except ValueError:
                target_step = 1
            target_step = max(1, min(8, target_step))
            return render_template(
                'financial_planner.html',
                current_step=target_step,
                plan_data=plan_data,
                error=None
            )

        try:
            # Step 1: Personal Details
            if step == '1':
                # Validation
                name = request.form.get('name', '').strip()
                age = request.form.get('age', '').strip()
                gender = request.form.get('gender', '').strip()
                city = request.form.get('city', '').strip()
                profession_type = request.form.get('profession_type', '').strip()
                work_experience = request.form.get('work_experience', '0').strip()
                marital_status = request.form.get('marital_status', '').strip()
                num_children = request.form.get('num_children', '0').strip()
                num_dependents = request.form.get('num_dependents', '0').strip()

                if not all([name, age, gender, city, profession_type, marital_status]):
                    return render_template('financial_planner.html',
                                         current_step=1,
                                         plan_data=plan_data,
                                         error="Please fill all required fields")

                try:
                    age_int = int(age)
                    if age_int < 18 or age_int > 100:
                        raise ValueError("Age must be between 18 and 100")
                except ValueError:
                    return render_template('financial_planner.html',
                                         current_step=1,
                                         plan_data=plan_data,
                                         error="Please enter a valid age")

                # Store data
                plan_data['name'] = name
                plan_data['age'] = age_int
                plan_data['gender'] = gender
                plan_data['city'] = city
                plan_data['profession_type'] = profession_type
                plan_data['work_experience'] = int(work_experience) if work_experience else 0
                plan_data['marital_status'] = marital_status
                plan_data['num_children'] = int(num_children) if num_children else 0
                plan_data['num_dependents'] = int(num_dependents) if num_dependents else 0

            # Step 2: Income
            elif step == '2':
                monthly_salary = request.form.get('monthly_salary', '0').strip()
                additional_income = request.form.get('additional_income', '0').strip()
                annual_salary_growth = request.form.get('annual_salary_growth', '0').strip()

                try:
                    salary_float = float(monthly_salary)
                    if salary_float <= 0:
                        return render_template('financial_planner.html',
                                             current_step=2,
                                             plan_data=plan_data,
                                             error="Monthly salary must be greater than 0")
                except ValueError:
                    return render_template('financial_planner.html',
                                         current_step=2,
                                         plan_data=plan_data,
                                         error="Please enter valid income numbers")

                plan_data['monthly_salary'] = salary_float
                plan_data['additional_income'] = float(additional_income) if additional_income else 0
                plan_data['annual_salary_growth'] = float(annual_salary_growth) if annual_salary_growth else 0

            # Step 3: Monthly Expenses
            elif step == '3':
                total_expenses = request.form.get('total_expenses', '0').strip()
                rent = request.form.get('rent', '0').strip()
                emi = request.form.get('emi', '0').strip()
                insurance_premium = request.form.get('insurance_premium', '0').strip()
                other_commitments = request.form.get('other_commitments', '0').strip()

                try:
                    total_exp_float = float(total_expenses)
                    if total_exp_float < 0:
                        raise ValueError("Expenses cannot be negative")
                except ValueError:
                    return render_template('financial_planner.html',
                                         current_step=3,
                                         plan_data=plan_data,
                                         error="Please enter valid expense numbers")

                plan_data['total_expenses'] = total_exp_float
                plan_data['rent'] = float(rent) if rent else 0
                plan_data['emi'] = float(emi) if emi else 0
                plan_data['insurance_premium'] = float(insurance_premium) if insurance_premium else 0
                plan_data['other_commitments'] = float(other_commitments) if other_commitments else 0

            # Step 4: Current Financial Position
            elif step == '4':
                emergency_fund = request.form.get('emergency_fund', '0').strip()
                savings = request.form.get('savings', '0').strip()
                fd = request.form.get('fd', '0').strip()
                gold = request.form.get('gold', '0').strip()
                mutual_funds = request.form.get('mutual_funds', '0').strip()
                stocks = request.form.get('stocks', '0').strip()
                epf = request.form.get('epf', '0').strip()
                ppf = request.form.get('ppf', '0').strip()
                nps = request.form.get('nps', '0').strip()
                other_investments = request.form.get('other_investments', '0').strip()
                loans = request.form.get('loans', '0').strip()
                credit_card_debt = request.form.get('credit_card_debt', '0').strip()

                plan_data['emergency_fund'] = float(emergency_fund) if emergency_fund else 0
                plan_data['savings'] = float(savings) if savings else 0
                plan_data['fd'] = float(fd) if fd else 0
                plan_data['gold'] = float(gold) if gold else 0
                plan_data['mutual_funds'] = float(mutual_funds) if mutual_funds else 0
                plan_data['stocks'] = float(stocks) if stocks else 0
                plan_data['epf'] = float(epf) if epf else 0
                plan_data['ppf'] = float(ppf) if ppf else 0
                plan_data['nps'] = float(nps) if nps else 0
                plan_data['other_investments'] = float(other_investments) if other_investments else 0
                plan_data['loans'] = float(loans) if loans else 0
                plan_data['credit_card_debt'] = float(credit_card_debt) if credit_card_debt else 0

            # Step 5: Protection
            elif step == '5':
                plan_data['health_insurance'] = request.form.get('health_insurance') == 'yes'
                plan_data['life_insurance'] = request.form.get('life_insurance') == 'yes'
                plan_data['term_insurance'] = request.form.get('term_insurance') == 'yes'
                plan_data['nominee_available'] = request.form.get('nominee_available') == 'yes'

            # Step 6: Life Goals
            elif step == '6':
                plan_data['goals'] = {}

                if request.form.get('goal_house') == 'yes':
                    house_age = request.form.get('goal_house_age', '').strip()
                    house_budget = request.form.get('goal_house_budget', '').strip()
                    if house_age and house_budget:
                        plan_data['goals']['house'] = {
                            'desired_age': int(house_age),
                            'budget': float(house_budget)
                        }

                if request.form.get('goal_car') == 'yes':
                    car_age = request.form.get('goal_car_age', '').strip()
                    car_budget = request.form.get('goal_car_budget', '').strip()
                    if car_age and car_budget:
                        plan_data['goals']['car'] = {
                            'desired_age': int(car_age),
                            'budget': float(car_budget)
                        }

                if request.form.get('goal_bike') == 'yes':
                    bike_age = request.form.get('goal_bike_age', '').strip()
                    bike_budget = request.form.get('goal_bike_budget', '').strip()
                    if bike_age and bike_budget:
                        plan_data['goals']['bike'] = {
                            'desired_age': int(bike_age),
                            'budget': float(bike_budget)
                        }

                if request.form.get('goal_marriage') == 'yes':
                    marriage_age = request.form.get('goal_marriage_age', '').strip()
                    if marriage_age:
                        plan_data['goals']['marriage'] = {'desired_age': int(marriage_age)}

                if request.form.get('goal_children') == 'yes':
                    children_age = request.form.get('goal_children_age', '').strip()
                    if children_age:
                        plan_data['goals']['children'] = {'desired_age': int(children_age)}

                if request.form.get('goal_foreign_trip') == 'yes':
                    trip_age = request.form.get('goal_foreign_trip_age', '').strip()
                    if trip_age:
                        plan_data['goals']['foreign_trip'] = {'desired_age': int(trip_age)}

                if request.form.get('goal_business') == 'yes':
                    business_age = request.form.get('goal_business_age', '').strip()
                    if business_age:
                        plan_data['goals']['business'] = {'desired_age': int(business_age)}

                if request.form.get('goal_education') == 'yes':
                    education_age = request.form.get('goal_education_age', '').strip()
                    if education_age:
                        plan_data['goals']['higher_education'] = {'desired_age': int(education_age)}

                if request.form.get('goal_parents') == 'yes':
                    parents_age = request.form.get('goal_parents_age', '').strip()
                    if parents_age:
                        plan_data['goals']['support_parents'] = {'desired_age': int(parents_age)}

                retirement_age = request.form.get('retirement_age', '60').strip()
                retirement_lifestyle = request.form.get('retirement_lifestyle', 'comfortable').strip()
                other_goals = request.form.get('other_goals', '').strip()

                plan_data['retirement_age'] = int(retirement_age) if retirement_age else 60
                plan_data['retirement_lifestyle'] = retirement_lifestyle
                if other_goals:
                    plan_data['other_goals'] = other_goals

            # Step 7: Risk Profile
            elif step == '7':
                risk_appetite = request.form.get('risk_appetite', '').strip()
                if not risk_appetite:
                    return render_template('financial_planner.html',
                                         current_step=7,
                                         plan_data=plan_data,
                                         error="Please select your risk appetite")
                plan_data['risk_appetite'] = risk_appetite

            # Step 8: Generate Plan
            elif step == '8':
                session['financial_plan'] = plan_data
                return redirect(url_for('financial_plan_results'))

            session['financial_plan'] = plan_data

            # Move to next step
            current_step_int = int(step)
            next_step = current_step_int + 1

            if next_step > 8:
                return redirect(url_for('financial_plan_results'))

            return render_template('financial_planner.html', current_step=next_step, plan_data=plan_data, error=None)

        except Exception as e:
            app.logger.error(f"Financial Planner Error: {str(e)}")
            return render_template('financial_planner.html',
                                 current_step=int(step),
                                 plan_data=plan_data,
                                 error=f"An error occurred: {str(e)}")

    # GET request - start from step 1
    return render_template('financial_planner.html', current_step=1, plan_data={}, error=None)
# =====================================================================
# REPLACE your existing `financial_plan_results` AND `download_financial_pdf`
# functions with everything below (including the new `_build_financial_results`
# helper). Do NOT touch `financial_planner` — it's already fixed and correct.
#
# ADD THESE IMPORTS at the top of app.py if they aren't already there:
#
#   import datetime
#   from io import BytesIO
#   from flask import send_file, flash, session, redirect, url_for, render_template
#   from reportlab.lib.pagesizes import A4
#   from reportlab.lib.units import cm
#   from reportlab.lib import colors
#   from reportlab.lib.enums import TA_CENTER, TA_LEFT
#   from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
#   from reportlab.platypus import (
#       SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
#       HRFlowable, PageBreak
#   )
#
# WHY THIS CHANGED
# ---------------------------------------------------------------------
# Your old download_financial_pdf() read raw session data directly and
# only ever wrote "Name: X" / "Age: Y" — none of the score, strengths,
# goals, retirement or roadmap calculations that financial_plan_results()
# computes were ever used. Rather than duplicate ~300 lines of scoring
# logic into the PDF route (and risk the two drifting apart over time),
# the calculation engine is now ONE function, `_build_financial_results`,
# used by both the web page and the PDF. Same numbers, everywhere.
# =====================================================================

# --------------------------------------------------------------------
# SHARED CALCULATION ENGINE
# --------------------------------------------------------------------

def _build_financial_results(plan_data):
    """
    Takes the raw session plan_data collected by the wizard and returns
    the fully computed `results` dict — score, snapshot, strengths,
    weaknesses, risks, recommendations, priorities, goal analysis,
    retirement plan, asset allocation and life roadmap.

    Used by BOTH financial_plan_results() (web page) and
    download_financial_pdf() (PDF report) so the two never disagree.
    """

    # --------------------------------------------------
    # PERSONAL DETAILS
    # --------------------------------------------------

    name = plan_data.get("name", "Friend")
    age = int(plan_data.get("age", 0))
    profession = plan_data.get("profession_type", "Professional")
    work_experience = int(plan_data.get("work_experience", 0))
    marital_status = plan_data.get("marital_status", "")
    dependents = int(plan_data.get("num_dependents", 0))
    children = int(plan_data.get("num_children", 0))

    # --------------------------------------------------
    # INCOME
    # --------------------------------------------------

    monthly_salary = float(plan_data.get("monthly_salary", 0))
    additional_income = float(plan_data.get("additional_income", 0))
    annual_salary_growth = float(plan_data.get("annual_salary_growth", 8))

    monthly_income = monthly_salary + additional_income
    annual_income = monthly_income * 12

    # --------------------------------------------------
    # EXPENSES
    # --------------------------------------------------

    monthly_expense = float(plan_data.get("total_expenses", 0))
    rent = float(plan_data.get("rent", 0))
    emi = float(plan_data.get("emi", 0))
    insurance_premium = float(plan_data.get("insurance_premium", 0))
    other_commitments = float(plan_data.get("other_commitments", 0))

    monthly_surplus = monthly_income - monthly_expense
    annual_surplus = monthly_surplus * 12

    # --------------------------------------------------
    # ASSETS
    # --------------------------------------------------

    emergency_fund = float(plan_data.get("emergency_fund", 0))
    savings = float(plan_data.get("savings", 0))
    fd = float(plan_data.get("fd", 0))
    gold = float(plan_data.get("gold", 0))
    mutual_funds = float(plan_data.get("mutual_funds", 0))
    stocks = float(plan_data.get("stocks", 0))
    epf = float(plan_data.get("epf", 0))
    ppf = float(plan_data.get("ppf", 0))
    nps = float(plan_data.get("nps", 0))
    other_investments = float(plan_data.get("other_investments", 0))

    total_assets = (
        emergency_fund + savings + fd + gold + mutual_funds +
        stocks + epf + ppf + nps + other_investments
    )

    # --------------------------------------------------
    # LIABILITIES
    # --------------------------------------------------

    loans = float(plan_data.get("loans", 0))
    credit_card_debt = float(plan_data.get("credit_card_debt", 0))
    total_liabilities = loans + credit_card_debt
    net_worth = total_assets - total_liabilities

    # --------------------------------------------------
    # CASH FLOW METRICS
    # --------------------------------------------------

    savings_rate = (monthly_surplus / monthly_income * 100) if monthly_income > 0 else 0
    expense_ratio = (monthly_expense / monthly_income * 100) if monthly_income > 0 else 0
    emergency_months = (emergency_fund / monthly_expense) if monthly_expense > 0 else 0
    debt_income_ratio = (total_liabilities / annual_income * 100) if annual_income > 0 else 0

    # --------------------------------------------------
    # ASSET ALLOCATION
    # --------------------------------------------------

    equity = mutual_funds + stocks
    debt_assets = savings + fd + epf + ppf + nps
    alternate_assets = gold + other_investments

    if total_assets > 0:
        equity_percent = (equity / total_assets) * 100
        debt_percent = (debt_assets / total_assets) * 100
        alternate_percent = (alternate_assets / total_assets) * 100
    else:
        equity_percent = 0
        debt_percent = 0
        alternate_percent = 0

    # --------------------------------------------------
    # INSURANCE & PROTECTION
    # --------------------------------------------------

    health_insurance = plan_data.get("health_insurance", False)
    life_insurance = plan_data.get("life_insurance", False)
    term_insurance = plan_data.get("term_insurance", False)
    nominee_available = plan_data.get("nominee_available", False)

    # --------------------------------------------------
    # RETIREMENT DETAILS
    # --------------------------------------------------

    retirement_age = int(plan_data.get("retirement_age", 60))
    retirement_lifestyle = plan_data.get("retirement_lifestyle", "comfortable")
    years_to_retirement = max(0, retirement_age - age)

    # --------------------------------------------------
    # INDIVIDUAL SCORES (0-100)
    # --------------------------------------------------

    cashflow_score = 0
    if savings_rate >= 40:
        cashflow_score = 100
    elif savings_rate >= 30:
        cashflow_score = 85
    elif savings_rate >= 20:
        cashflow_score = 70
    elif savings_rate >= 10:
        cashflow_score = 50
    elif savings_rate > 0:
        cashflow_score = 30

    protection_score = 0
    if health_insurance:
        protection_score += 35
    if term_insurance:
        protection_score += 40
    if life_insurance:
        protection_score += 15
    if nominee_available:
        protection_score += 10
    protection_score = min(100, protection_score)

    debt_score = 100
    if debt_income_ratio > 150:
        debt_score = 20
    elif debt_income_ratio > 100:
        debt_score = 40
    elif debt_income_ratio > 75:
        debt_score = 60
    elif debt_income_ratio > 50:
        debt_score = 75
    elif debt_income_ratio > 25:
        debt_score = 90

    wealth_score = 0
    if annual_income > 0:
        wealth_multiple = net_worth / annual_income
        if wealth_multiple >= 5:
            wealth_score = 100
        elif wealth_multiple >= 3:
            wealth_score = 85
        elif wealth_multiple >= 2:
            wealth_score = 70
        elif wealth_multiple >= 1:
            wealth_score = 55
        elif wealth_multiple > 0:
            wealth_score = 35

    retirement_score = 0
    if years_to_retirement >= 25:
        retirement_score = 90
    elif years_to_retirement >= 15:
        retirement_score = 75
    elif years_to_retirement >= 10:
        retirement_score = 60
    elif years_to_retirement >= 5:
        retirement_score = 40
    else:
        retirement_score = 25

    investment_types = sum([
        mutual_funds > 0, stocks > 0, fd > 0,
        epf > 0, ppf > 0, nps > 0, gold > 0
    ])
    diversification_score = min(100, investment_types * 15)

    financial_score = int(
        cashflow_score * 0.25 +
        protection_score * 0.20 +
        debt_score * 0.15 +
        wealth_score * 0.20 +
        retirement_score * 0.10 +
        diversification_score * 0.10
    )

    # --------------------------------------------------
    # PERSONALIZED INSIGHTS
    # --------------------------------------------------

    strengths = []
    weaknesses = []
    risks = []
    recommendations = []

    if savings_rate >= 30:
        strengths.append(f"You save {savings_rate:.1f}% of your income, which is excellent.")
    elif savings_rate >= 20:
        strengths.append(f"You have a healthy savings rate of {savings_rate:.1f}%.")
    elif savings_rate >= 10:
        weaknesses.append("Your savings rate is moderate. Aim for at least 20%.")
    else:
        weaknesses.append("Your savings rate is very low.")
        risks.append("Low monthly savings can delay every future financial goal.")

    if emergency_months >= 12:
        strengths.append("Excellent emergency fund covering more than one year.")
    elif emergency_months >= 6:
        strengths.append("Emergency fund is financially strong.")
    elif emergency_months >= 3:
        recommendations.append("Increase emergency fund to six months of expenses.")
    else:
        weaknesses.append("Emergency fund is insufficient.")
        risks.append("Unexpected expenses may force you to borrow money.")

    if total_liabilities == 0:
        strengths.append("Debt free. This gives tremendous financial flexibility.")
    elif debt_income_ratio > 100:
        weaknesses.append("Debt exceeds your annual income.")
        risks.append("High debt burden may slow wealth creation.")
    elif debt_income_ratio > 50:
        recommendations.append("Prioritize reducing outstanding debt.")

    if health_insurance:
        strengths.append("Health insurance protection is available.")
    else:
        weaknesses.append("Health insurance is missing.")
        risks.append("One medical emergency can significantly impact your finances.")

    if dependents > 0:
        if term_insurance:
            strengths.append("Family is protected through term insurance.")
        else:
            weaknesses.append("You have dependents but no term insurance.")
            risks.append("Family income protection is inadequate.")

    if net_worth >= annual_income * 2:
        strengths.append("Your net worth is growing strongly.")
    elif net_worth <= 0:
        weaknesses.append("Current net worth is zero or negative.")
        recommendations.append("Focus on increasing assets while reducing liabilities.")

    if investment_types >= 5:
        strengths.append("Your investments are well diversified.")
    elif investment_types >= 3:
        recommendations.append("Diversify gradually across equity, debt and retirement products.")
    else:
        weaknesses.append("Investment portfolio lacks diversification.")

    if years_to_retirement >= 20:
        strengths.append("You still have sufficient time for compounding.")
    elif years_to_retirement <= 10:
        recommendations.append("Retirement planning should become your highest priority.")

    if monthly_surplus <= 0:
        risks.append("Your monthly expenses exceed your income.")
        recommendations.append("Reduce expenses immediately before starting investments.")
    elif monthly_surplus < monthly_income * 0.15:
        recommendations.append("Increase monthly surplus to improve future wealth creation.")

    # --------------------------------------------------
    # GOAL ANALYSIS
    # --------------------------------------------------

    goals = plan_data.get("goals", {})
    goal_analysis = []
    inflation = 0.06
    expected_return = 0.12
    available_sip = max(0, monthly_surplus * 0.80)

    for goal_name, goal in goals.items():
        desired_age = int(goal.get("desired_age", age))
        years = max(1, desired_age - age)
        present_cost = float(goal.get("budget", 0))
        if present_cost <= 0:
            continue

        future_cost = present_cost * ((1 + inflation) ** years)
        monthly_rate = expected_return / 12
        months = years * 12

        if monthly_rate > 0:
            required_sip = future_cost * monthly_rate / (((1 + monthly_rate) ** months) - 1)
        else:
            required_sip = future_cost / months

        if available_sip >= required_sip:
            status, status_color = "Achievable", "green"
            message = "Based on your current surplus, this goal is achievable."
        elif available_sip >= required_sip * 0.75:
            status, status_color = "Needs Improvement", "orange"
            message = "Increase your monthly investment slightly to comfortably achieve this goal."
        else:
            status, status_color = "At Risk", "red"
            message = "Your current financial capacity is insufficient for this goal."

        goal_analysis.append({
            "goal": goal_name.replace("_", " ").title(),
            "current_cost": present_cost,
            "future_cost": future_cost,
            "years_remaining": years,
            "required_sip": required_sip,
            "available_sip": available_sip,
            "status": status,
            "status_color": status_color,
            "message": message
        })

    goal_analysis.sort(key=lambda x: x["years_remaining"])

    # --------------------------------------------------
    # RETIREMENT CORPUS
    # --------------------------------------------------

    retirement_expense = monthly_expense * 0.70
    future_monthly_expense = retirement_expense * ((1 + inflation) ** years_to_retirement)
    retirement_corpus = future_monthly_expense * 12 * 25

    retirement_monthly_sip = 0
    if years_to_retirement > 0:
        months = years_to_retirement * 12
        monthly_rate = expected_return / 12
        retirement_monthly_sip = retirement_corpus * monthly_rate / (((1 + monthly_rate) ** months) - 1)

    retirement_status = "On Track" if available_sip >= retirement_monthly_sip else "Needs Higher Investment"

    # --------------------------------------------------
    # TOP PRIORITIES
    # --------------------------------------------------

    priorities = []

    if emergency_months < 6:
        priorities.append({
            "title": "Build Emergency Fund",
            "description": f"Increase your emergency fund to at least Rs. {monthly_expense*6:,.0f}.",
            "priority": "High"
        })
    if not health_insurance:
        priorities.append({
            "title": "Purchase Health Insurance",
            "description": "Protect yourself against unexpected medical expenses.",
            "priority": "Critical"
        })
    if dependents > 0 and not term_insurance:
        priorities.append({
            "title": "Purchase Term Insurance",
            "description": f"Recommended cover: Rs. {annual_income*15:,.0f}.",
            "priority": "Critical"
        })
    if savings_rate < 20:
        priorities.append({
            "title": "Increase Savings Rate",
            "description": "Target saving at least 20% of your monthly income.",
            "priority": "High"
        })
    if total_liabilities > 0:
        priorities.append({
            "title": "Reduce Debt",
            "description": "Pay off high-interest loans before increasing investments.",
            "priority": "High"
        })
    if investment_types < 4:
        priorities.append({
            "title": "Diversify Investments",
            "description": "Build a balanced portfolio across Equity, Debt and Retirement products.",
            "priority": "Medium"
        })
    if available_sip < retirement_monthly_sip:
        priorities.append({
            "title": "Increase Retirement Investment",
            "description": f"Required monthly retirement SIP: Rs. {retirement_monthly_sip:,.0f}.",
            "priority": "High"
        })

    # --------------------------------------------------
    # RECOMMENDED ASSET ALLOCATION
    # --------------------------------------------------

    equity_allocation = max(30, min(80, 100 - age))
    debt_allocation = 100 - equity_allocation

    recommended_portfolio = {
        "Equity": equity_allocation,
        "Debt": debt_allocation,
        "Emergency Fund": 6,
        "Gold": 10 if age > 35 else 5
    }

    # --------------------------------------------------
    # LIFE ROADMAP
    # --------------------------------------------------

    roadmap = [{
        "age": age,
        "title": "Current Position",
        "description": "Begin disciplined financial planning."
    }]

    if emergency_months < 6:
        roadmap.append({
            "age": age + 1,
            "title": "Emergency Fund Completed",
            "description": "Maintain six months of expenses."
        })

    for item in goal_analysis:
        roadmap.append({
            "age": age + item["years_remaining"],
            "title": item["goal"],
            "description": item["status"]
        })

    roadmap.append({
        "age": retirement_age,
        "title": "Financial Independence",
        "description": retirement_status
    })

    roadmap.sort(key=lambda x: x["age"])

    # --------------------------------------------------
    # OVERALL FINANCIAL STATUS
    # --------------------------------------------------

    if financial_score >= 85:
        overall_status = "Excellent"
    elif financial_score >= 70:
        overall_status = "Very Good"
    elif financial_score >= 55:
        overall_status = "Good"
    elif financial_score >= 40:
        overall_status = "Needs Improvement"
    else:
        overall_status = "Critical"

    overall_summary = (
        f"{name}, your current financial score is {financial_score}/100. "
        f"You save {savings_rate:.1f}% of your monthly income and currently "
        f"have a net worth of Rs. {net_worth:,.0f}. Following the recommendations "
        f"below can significantly improve your financial future."
    )

    # --------------------------------------------------
    # RESULTS OBJECT
    # --------------------------------------------------

    return {
        "name": name, "age": age, "profession": profession,
        "work_experience": work_experience, "marital_status": marital_status,
        "dependents": dependents, "children": children,

        "monthly_income": monthly_income, "annual_income": annual_income,
        "monthly_expense": monthly_expense, "monthly_surplus": monthly_surplus,
        "annual_surplus": annual_surplus,

        "total_assets": total_assets, "total_liabilities": total_liabilities,
        "net_worth": net_worth,

        "savings_rate": round(savings_rate, 2), "expense_ratio": round(expense_ratio, 2),
        "emergency_months": round(emergency_months, 1),
        "debt_income_ratio": round(debt_income_ratio, 2),

        "equity_percent": round(equity_percent, 1), "debt_percent": round(debt_percent, 1),
        "alternate_percent": round(alternate_percent, 1),

        "financial_score": financial_score, "cashflow_score": cashflow_score,
        "protection_score": protection_score, "wealth_score": wealth_score,
        "debt_score": debt_score, "retirement_score": retirement_score,
        "diversification_score": diversification_score,

        "overall_status": overall_status, "overall_summary": overall_summary,

        "health_insurance": health_insurance, "life_insurance": life_insurance,
        "term_insurance": term_insurance, "nominee_available": nominee_available,

        "retirement_age": retirement_age, "years_to_retirement": years_to_retirement,
        "retirement_lifestyle": retirement_lifestyle, "retirement_corpus": retirement_corpus,
        "retirement_monthly_sip": retirement_monthly_sip, "retirement_status": retirement_status,

        "recommended_portfolio": recommended_portfolio,
        "goal_analysis": goal_analysis,
        "roadmap": roadmap,

        "strengths": strengths, "weaknesses": weaknesses,
        "risks": risks, "recommendations": recommendations, "priorities": priorities,

        "plan_data": plan_data
    }


# --------------------------------------------------------------------
# WEB RESULTS PAGE (unchanged behaviour — now just calls the helper)
# --------------------------------------------------------------------

@app.route('/financial-plan-results')
def financial_plan_results():
    """
    SmartPlanFinance Personal Financial Planner
    Generates a complete personalized financial roadmap.
    """

    if 'financial_plan' not in session:
        return redirect(url_for('financial_planner'))

    try:
        plan_data = session['financial_plan']
        results = _build_financial_results(plan_data)
        return render_template('financial_plan_results.html', results=results)

    except Exception as e:
        app.logger.exception(f"Financial Planner Error : {e}")
        flash("Unable to generate your financial plan. Please try again.", "danger")
        return redirect(url_for("financial_planner"))


# --------------------------------------------------------------------
# PDF REPORT — now a complete, branded, multi-section roadmap
# --------------------------------------------------------------------

def _fmt_money(amount):
    """PDF-safe currency formatting. Avoids the Rupee glyph (₹) since
    ReportLab's default Helvetica font does not render it reliably."""
    return "Rs. {:,.0f}".format(amount)


@app.route('/download-financial-pdf')
def download_financial_pdf():

    if 'financial_plan' not in session:
        return redirect(url_for('financial_planner'))

    try:
        plan_data = session['financial_plan']
        results = _build_financial_results(plan_data)
    except Exception as e:
        app.logger.exception(f"PDF Generation Error : {e}")
        flash("Unable to generate your PDF report. Please try again.", "danger")
        return redirect(url_for('financial_planner'))

    GOLD = colors.HexColor('#B99120')
    GOLD_BG = colors.HexColor('#FFF7D6')
    GREEN = colors.HexColor('#0B7A3D')
    GREEN_BG = colors.HexColor('#F0FFF5')
    ORANGE_BG = colors.HexColor('#FFF3E0')
    RED_BG = colors.HexColor('#FFEBEE')
    DARK = colors.HexColor('#222222')
    GRAY = colors.HexColor('#666666')
    BORDER = colors.HexColor('#EFE7CC')

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Brand', fontName='Helvetica-Bold', fontSize=12,
                               textColor=GREEN, spaceAfter=2))
    styles.add(ParagraphStyle(name='ReportTitle', fontName='Helvetica-Bold', fontSize=22,
                               textColor=GOLD, spaceAfter=4))
    styles.add(ParagraphStyle(name='ByLine', fontName='Helvetica', fontSize=10,
                               textColor=GRAY, spaceAfter=10))
    styles.add(ParagraphStyle(name='SectionHeading', fontName='Helvetica-Bold', fontSize=14,
                               textColor=GOLD, spaceBefore=16, spaceAfter=8))
    styles.add(ParagraphStyle(name='SubHeading', fontName='Helvetica-Bold', fontSize=11,
                               textColor=DARK, spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle(name='BodyGray', fontName='Helvetica', fontSize=10,
                               textColor=DARK, leading=15))
    styles.add(ParagraphStyle(name='BulletGreen', fontName='Helvetica', fontSize=10,
                               textColor=DARK, leading=14, spaceAfter=4, leftIndent=10))
    styles.add(ParagraphStyle(name='BulletOrange', fontName='Helvetica', fontSize=10,
                               textColor=DARK, leading=14, spaceAfter=4, leftIndent=10))
    styles.add(ParagraphStyle(name='BulletRed', fontName='Helvetica', fontSize=10,
                               textColor=DARK, leading=14, spaceAfter=4, leftIndent=10))
    styles.add(ParagraphStyle(name='DisclaimerText', fontName='Helvetica-Oblique', fontSize=8.5,
                               textColor=GRAY, leading=12))

    def table_header_style(extra=None):
        cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), GOLD),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9.5),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GOLD_BG]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]
        if extra:
            cmds.extend(extra)
        return TableStyle(cmds)

    def footer(canvas_obj, doc):
        canvas_obj.saveState()
        canvas_obj.setStrokeColor(BORDER)
        canvas_obj.line(1.8 * cm, 1.3 * cm, A4[0] - 1.8 * cm, 1.3 * cm)
        canvas_obj.setFont('Helvetica-Bold', 8)
        canvas_obj.setFillColor(GOLD)
        canvas_obj.drawString(1.8 * cm, 0.9 * cm, "SmartPlanFinance")
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.setFillColor(GRAY)
        canvas_obj.drawRightString(A4[0] - 1.8 * cm, 0.9 * cm, f"Page {doc.page}")
        canvas_obj.restoreState()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        title="SmartPlanFinance Financial Roadmap",
        topMargin=1.8 * cm, bottomMargin=2 * cm,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm
    )

    story = []
    usable_width = A4[0] - 3.6 * cm  # page width minus left+right margins

    # ---------------- HEADER ----------------
    story.append(Paragraph("SMARTPLANFINANCE", styles['Brand']))
    story.append(Paragraph("Your Personal Financial Roadmap", styles['ReportTitle']))
    story.append(Paragraph(
        f"Prepared for <b>{results['name']}</b> (Age {results['age']}) &nbsp;|&nbsp; "
       f"Generated on {date.today().strftime('%d %B %Y')}",
        styles['ByLine']
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=10))

    # ---------------- SCORE + SUMMARY ----------------
    story.append(Paragraph(
        f"Financial Health Score: <font color='#B99120'>{results['financial_score']}/100</font> "
        f"&mdash; {results['overall_status']}",
        styles['SectionHeading']
    ))
    story.append(Paragraph(results['overall_summary'], styles['BodyGray']))

    score_table = Table(
        [
            ["Cash Flow", "Protection", "Debt", "Wealth", "Retirement", "Diversification"],
            [
                f"{results['cashflow_score']}/100", f"{results['protection_score']}/100",
                f"{results['debt_score']}/100", f"{results['wealth_score']}/100",
                f"{results['retirement_score']}/100", f"{results['diversification_score']}/100",
            ]
        ],
        colWidths=[usable_width / 6.0] * 6
    )
    score_table.setStyle(table_header_style([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(Spacer(1, 8))
    story.append(score_table)

    # ---------------- FINANCIAL SNAPSHOT ----------------
    story.append(Paragraph("Financial Snapshot", styles['SectionHeading']))
    snapshot_rows = [
        ["Metric", "Value"],
        ["Monthly Income", _fmt_money(results['monthly_income'])],
        ["Monthly Expenses", _fmt_money(results['monthly_expense'])],
        ["Monthly Surplus", _fmt_money(results['monthly_surplus'])],
        ["Net Worth", _fmt_money(results['net_worth'])],
        ["Savings Rate", f"{results['savings_rate']}%"],
        ["Emergency Fund Coverage", f"{results['emergency_months']} months"],
    ]
    snapshot_table = Table(snapshot_rows, colWidths=[usable_width * 0.55, usable_width * 0.45])
    snapshot_table.setStyle(table_header_style([('ALIGN', (1, 0), (1, -1), 'RIGHT')]))
    story.append(snapshot_table)

    # ---------------- STRENGTHS / WEAKNESSES / RISKS ----------------
    def bullet_block(title, items, marker, style_name, empty_text):
        story.append(Paragraph(title, styles['SubHeading']))
        if items:
            for item in items:
                story.append(Paragraph(f"{marker} {item}", styles[style_name]))
        else:
            story.append(Paragraph(empty_text, styles['BodyGray']))

    story.append(Paragraph("Strengths, Weaknesses &amp; Risks", styles['SectionHeading']))
    bullet_block("Financial Strengths", results['strengths'], "&#10004;", 'BulletGreen',
                 "No major strengths identified yet. Continue improving your financial habits.")
    bullet_block("Areas of Improvement", results['weaknesses'], "&#8226;", 'BulletOrange',
                 "Excellent! No major weaknesses detected.")
    bullet_block("Financial Risks", results['risks'], "&#9888;", 'BulletRed',
                 "No immediate financial risks detected.")

    # ---------------- RECOMMENDATIONS ----------------
    story.append(Paragraph("Personalized Recommendations", styles['SectionHeading']))
    if results['recommendations']:
        for rec in results['recommendations']:
            story.append(Paragraph(f"&#10003; {rec}", styles['BulletGreen']))
    else:
        story.append(Paragraph("Continue maintaining your current financial discipline.", styles['BodyGray']))

    # ---------------- TOP PRIORITIES ----------------
    story.append(Paragraph("Top Financial Priorities", styles['SectionHeading']))
    if results['priorities']:
        priority_rows = [["Priority", "Action", "Details"]]
        for p in results['priorities']:
            priority_rows.append([p['priority'], p['title'], p['description']])
        priority_table = Table(priority_rows, colWidths=[usable_width * 0.15, usable_width * 0.30, usable_width * 0.55])
        priority_table.setStyle(table_header_style())
        story.append(priority_table)
    else:
        story.append(Paragraph("Great financial discipline — no immediate priorities detected.", styles['BodyGray']))

    story.append(PageBreak())

    # ---------------- GOAL ANALYSIS ----------------
    story.append(Paragraph("Goal-wise SIP Analysis", styles['SectionHeading']))
    if results['goal_analysis']:
        goal_rows = [["Goal", "Years", "Future Cost", "Required SIP/mo", "Status"]]
        for g in results['goal_analysis']:
            goal_rows.append([
                g['goal'], str(g['years_remaining']),
                _fmt_money(g['future_cost']), _fmt_money(g['required_sip']),
                g['status']
            ])
        goal_table = Table(goal_rows, colWidths=[
            usable_width * 0.24, usable_width * 0.10, usable_width * 0.24,
            usable_width * 0.24, usable_width * 0.18
        ])
        goal_table.setStyle(table_header_style([('ALIGN', (1, 0), (-1, -1), 'CENTER')]))
        story.append(goal_table)
        story.append(Spacer(1, 6))
        for g in results['goal_analysis']:
            story.append(Paragraph(f"<b>{g['goal']}:</b> {g['message']}", styles['BodyGray']))
    else:
        story.append(Paragraph("No goals were added. Add life goals in the planner for a personalized "
                                "goal-by-goal investment plan.", styles['BodyGray']))

    # ---------------- RETIREMENT PLANNING ----------------
    story.append(Paragraph("Retirement Planning", styles['SectionHeading']))
    retirement_rows = [
        ["Metric", "Value"],
        ["Retirement Age", str(results['retirement_age'])],
        ["Years Remaining", str(results['years_to_retirement'])],
        ["Estimated Corpus Required", _fmt_money(results['retirement_corpus'])],
        ["Monthly SIP Required", _fmt_money(results['retirement_monthly_sip'])],
        ["Status", results['retirement_status']],
    ]
    retirement_table = Table(retirement_rows, colWidths=[usable_width * 0.55, usable_width * 0.45])
    retirement_table.setStyle(table_header_style([('ALIGN', (1, 0), (1, -1), 'RIGHT')]))
    story.append(retirement_table)

    # ---------------- ASSET ALLOCATION ----------------
    story.append(Paragraph("Asset Allocation", styles['SectionHeading']))
    story.append(Paragraph("Recommended Portfolio", styles['SubHeading']))
    rec_rows = [["Asset Class", "Recommended %"]]
    for asset, pct in results['recommended_portfolio'].items():
        rec_rows.append([asset, f"{pct}%"])
    rec_table = Table(rec_rows, colWidths=[usable_width * 0.6, usable_width * 0.4])
    rec_table.setStyle(table_header_style([('ALIGN', (1, 0), (1, -1), 'RIGHT')]))
    story.append(rec_table)

    story.append(Paragraph("Your Current Distribution", styles['SubHeading']))
    cur_rows = [
        ["Asset Class", "Current %"],
        ["Equity", f"{results['equity_percent']}%"],
        ["Debt", f"{results['debt_percent']}%"],
        ["Gold / Alternative", f"{results['alternate_percent']}%"],
    ]
    cur_table = Table(cur_rows, colWidths=[usable_width * 0.6, usable_width * 0.4])
    cur_table.setStyle(table_header_style([('ALIGN', (1, 0), (1, -1), 'RIGHT')]))
    story.append(cur_table)

    # ---------------- LIFE ROADMAP ----------------
    story.append(Paragraph("Your Financial Life Roadmap", styles['SectionHeading']))
    roadmap_rows = [["Age", "Milestone", "Notes"]]
    for item in results['roadmap']:
        roadmap_rows.append([str(item['age']), item['title'], item['description']])
    roadmap_table = Table(roadmap_rows, colWidths=[usable_width * 0.12, usable_width * 0.38, usable_width * 0.50])
    roadmap_table.setStyle(table_header_style())
    story.append(roadmap_table)

    # ---------------- DISCLAIMER ----------------
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=8))
    story.append(Paragraph(
        "<b>Disclaimer:</b> This financial roadmap is created for educational purposes only, based on the "
        "information provided by you and general financial planning assumptions (6% inflation, 12% expected "
        "equity returns). It is not personalized investment advice. Please consult a qualified financial "
        "advisor before making important financial decisions. SmartPlanFinance does not guarantee future "
        "returns or outcomes.",
        styles['DisclaimerText']
    ))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)

    safe_name = "".join(c for c in results['name'] if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_') or "User"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"SmartPlanFinance_Report_{safe_name}.pdf",
        mimetype="application/pdf"
    )

@app.route("/download-report")
@login_required
def download_report():

    user_id = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    # User
    cur.execute(
        "SELECT * FROM users WHERE id=%s",
        (user_id,)
    )
    user = cur.fetchone()

    # Latest Report
    cur.execute("""
        SELECT *
        FROM reports
        WHERE user_id=%s
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id,))

    report = cur.fetchone()

    conn.close()

    if not report:
        return redirect(url_for("dashboard"))

    savings = report["savings"]
    risk = report["risk"].lower()

    rules = RISK_RULES.get(
        risk,
        RISK_RULES["medium"]
    )

    # Financial Score
    savings_rate = (
        report["savings"] / report["income"]
    ) * 100 if report["income"] > 0 else 0

    score = int(40 + (savings_rate * 0.7))
    score = min(score, 99)

    # Complete report data
    data = {

    "income": report["income"],
    "expense": report["expense"],
    "savings": savings,

    "score": score,

    "risk": risk.capitalize(),

    "sip": savings * rules["sip"],
    "large_cap": savings * rules["large_cap"],
    "mid_cap": savings * rules["mid_cap"],
    "small_cap": savings * rules["small_cap"],
    "emergency_fund": savings * rules["emergency"],

    "advice": ADVISOR_INSIGHTS.get(risk, []),

    # SIP
    "sip_calc_monthly": report["sip_calc_monthly"] or 0,
    "sip_calc_years": report["sip_calc_years"] or 0,
    "sip_calc_fv": report["sip_calc_fv"] or 0,

    # Financial Goal
    "future_target_amount": report["future_target_amount"] or 0,
    "future_target_years": report["future_target_years"] or 0,
    "future_req_monthly": report["future_req_monthly"] or 0,

    # EMI
    "emi_loan_amount": report["emi_loan_amount"] or 0,
    "emi_rate": report["emi_rate"] or 0,
    "emi_years": report["emi_years"] or 0,
    "emi_monthly": report["emi_monthly"] or 0,
    "emi_interest": report["emi_interest"] or 0,
    "emi_total": report["emi_total"] or 0,

    # Retirement
    "retirement_corpus": report["retirement_corpus"] or 0,
    "retirement_monthly": report["retirement_monthly"] or 0,
    "retirement_age": report["retirement_age"] or 0,

    # FD
    "fd_principal": report["fd_principal"] or 0,
    "fd_rate": report["fd_rate"] or 0,
    "fd_years": report["fd_years"] or 0,
    "fd_interest": report["fd_interest"] or 0,
    "fd_maturity": report["fd_maturity"] or 0,

    # Tax
    "tax_income": report["tax_income"] or 0,
    "tax_old": report["tax_old"] or 0,
    "tax_new": report["tax_new"] or 0,
    "tax_savings": report["tax_savings"] or 0,
    "tax_better": report["tax_better"] or ""

}

    unique_filename = f"financial_report_{uuid.uuid4().hex}.pdf"
    pdf_path = os.path.join(tempfile.gettempdir(), unique_filename)

    generate_financial_report(
        pdf_path,
        user,
        data
    )

    response = send_file(
        pdf_path,
        as_attachment=True,
        download_name="SmartPlan_Finance_Report.pdf"
    )


    @response.call_on_close
    def cleanup():
        try:
            os.remove(pdf_path)
        except OSError:
            pass

    return response

# Warm-up article caches after all routes are registered.
init_db()

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=False
    )
