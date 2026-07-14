import re
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, url_for, Response
from functools import wraps
from config import COUNTRIES
from dotenv import load_dotenv
from functools import wraps
from flask import session, redirect, url_for
from flask import send_file
from pdf_generator import generate_financial_report
from flask import send_file
from openai import OpenAI
import FAQ
import logging
from article_prompt import MASTER_ARTICLE_PROMPT
from flask import jsonify
from prompts import ARTICLE_PROMPT
from knowledge_base import INTERNAL_LINKS
logging.basicConfig(level=logging.INFO)

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
print("Groq Key Found:", GROQ_API_KEY is not None)
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)
app = Flask(__name__)
# Make sure this matches your production environment
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "smartplanfinance-dev-secret"
)

# --- SECURITY GUARD (ADMIN AUTHENTICATION) ---
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
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function
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
        cursor_factory=RealDictCursor,  # Added the comma here             # Changed 'require' to 'prefer'
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
@app.route("/reset-session")
@requires_auth
def reset_session():
    session.clear()
    return "✅ Session cleared."
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

    user_message = request.json.get("message", "")

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
            "reply": completion.choices[0].message.content
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
    return redirect(url_for('articles'))

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        name = request.form.get('name')
        mobile = request.form.get('mobile')
        country = request.form.get('country')

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id FROM users WHERE mobile = %s",
            (mobile,)
        )

        existing_user = cur.fetchone()

        if existing_user:

            user_id = existing_user["id"]

            # Update latest user details
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

            cur.execute("""
                INSERT INTO users
                (
                    name,
                    mobile,
                    country
                )
                VALUES
                (
                    %s,
                    %s,
                    %s
                )
                RETURNING id
            """, (
                name,
                mobile,
                country
            ))

            conn.commit()

            user_id = cur.fetchone()["id"]

        conn.close()

        session["user_id"] = user_id

        return redirect(url_for("profile"))

    return render_template(
        "login.html",
        countries=COUNTRIES.keys()
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

        cur.execute("""
            INSERT INTO reports
            (
                user_id,
                income,
                expense,
                savings,
                risk,
                created_at
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
    report_data["ai_advice"] = generate_ai_advice(report_data)
    return render_template('report.html', user=user, data=report_data)

@app.route('/sip-calculator', methods=['GET', 'POST'])
@login_required
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

        if 'user_id' in session:

            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute("""
                UPDATE reports
                SET sip_calc_monthly = %s,
                    sip_calc_years = %s,
                    sip_calc_fv = %s
                WHERE id = (
                    SELECT id
                    FROM reports
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                )
            """,
            (
                P,
                years,
                fv,
                session['user_id']
            ))

            conn.commit()
            conn.close()

    return render_template(
        'sip_calculator.html',
        result=result
    )

@app.route('/financial-future', methods=['GET', 'POST'])
@login_required
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
            req_monthly = target / (((1 + m_rate) ** months - 1) / m_rate) / (1 + m_rate)

        if 'user_id' in session:

            conn = get_db_connection()
            cur = conn.cursor()

            # Update user table
            cur.execute(
                """
                UPDATE users
                SET target_amount = %s,
                    target_years = %s
                WHERE id = %s
                """,
                (
                    target,
                    years,
                    session['user_id']
                )
            )

            # Always update the latest report for this user
            cur.execute(
                """
                UPDATE reports
                SET future_target_amount = %s,
                    future_target_years = %s,
                    future_req_monthly = %s
                WHERE id = (
                    SELECT id
                    FROM reports
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                )
                """,
                (
                    target,
                    years,
                    req_monthly,
                    session['user_id']
                )
            )

            conn.commit()
            conn.close()

        result = {
            "monthly_total": "{:,.2f}".format(req_monthly),
            "breakdown": {
                "sip": {
                    "amount": "{:,.2f}".format(req_monthly * 0.4),
                    "return": "12%"
                },
                "large": {
                    "label": "Large Cap",
                    "amount": "{:,.2f}".format(req_monthly * 0.3),
                    "return": "10%"
                },
                "mid": {
                    "label": "Mid Cap",
                    "amount": "{:,.2f}".format(req_monthly * 0.2),
                    "return": "15%"
                },
                "small": {
                    "label": "Small Cap",
                    "amount": "{:,.2f}".format(req_monthly * 0.1),
                    "return": "18%"
                }
            }
        }

    return render_template(
        'financial_future.html',
        result=result
    )
@app.route('/tax_calculator', methods=['GET', 'POST'])
@login_required
def tax_calculator():

    result = None

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
            chunk = min(max(0, remaining), limit)
            tax_new += chunk * rate
            remaining -= limit

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
        # SAVE TO REPORT
        # -----------------------------

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE reports
            SET
                tax_income=%s,
                tax_old=%s,
                tax_new=%s,
                tax_savings=%s,
                tax_better=%s
            WHERE id=(
                SELECT id
                FROM reports
                WHERE user_id=%s
                ORDER BY created_at DESC
                LIMIT 1
            )
        """,
        (
            income,
            tax_old,
            tax_new,
            savings,
            better_option,
            session["user_id"]
        ))

        conn.commit()
        conn.close()


        result = {
            "income": income,
            "old_regime": tax_old,
            "new_regime": tax_new,
            "savings": savings,
            "better_option": better_option
        }

    return render_template(
        "tax_calculator.html",
        result=result
    )
@app.route("/emi_calculator", methods=["GET", "POST"])
@login_required
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
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE reports
            SET
                emi_loan_amount=%s,
                emi_rate=%s,
                emi_years=%s,
                emi_monthly=%s,
                emi_interest=%s,
                emi_total=%s
            WHERE id=(
                SELECT id
                FROM reports
                WHERE user_id=%s
                ORDER BY created_at DESC
                LIMIT 1
            )
        """,(
            loan_amount,
            annual_rate,
            tenure_years,
            emi,
            total_interest,
            total_payment,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        result = {
            "loan_amount": loan_amount,
            "rate": annual_rate,
            "years": tenure_years,
            "emi": emi,
            "interest": total_interest,
            "total": total_payment
        }

    return render_template(
        "emi_calculator.html",
        result=result
    )
@app.route("/retirement_calculator", methods=["GET", "POST"])
@login_required
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

        years = retirement_age - current_age

        retirement_amount = (
            monthly_expense
            * 12
            * ((1 + inflation) ** years)
            * 25
        )

        monthly_return = expected_return / 12
        months = years * 12

        monthly_investment = (
            retirement_amount
            * monthly_return
            / (((1 + monthly_return) ** months) - 1)
        )

        # Save into latest report

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE reports
            SET
                retirement_corpus=%s,
                retirement_monthly=%s,
                retirement_age=%s
            WHERE id=(
                SELECT id
                FROM reports
                WHERE user_id=%s
                ORDER BY created_at DESC
                LIMIT 1
            )
        """,
        (
            retirement_amount,
            monthly_investment,
            retirement_age,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        result = {
            "corpus": retirement_amount,
            "monthly": monthly_investment,
            "age": retirement_age
        }

    return render_template(
        "retirement_calculator.html",
        result=result
    )
@app.route("/fd_calculator", methods=["GET", "POST"])
@login_required
def fd_calculator():

    result = None

    if request.method == "POST":

        principal = float(request.form.get("principal") or 0)
        rate = float(request.form.get("rate") or 0)
        years = float(request.form.get("years") or 0)

        r = rate / 100
        n = 4

        maturity_amount = principal * ((1 + (r / n)) ** (n * years))
        interest_earned = maturity_amount - principal

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE reports
            SET
                fd_principal=%s,
                fd_rate=%s,
                fd_years=%s,
                fd_interest=%s,
                fd_maturity=%s
            WHERE id=(
                SELECT id
                FROM reports
                WHERE user_id=%s
                ORDER BY created_at DESC
                LIMIT 1
            )
        """,
        (
            principal,
            rate,
            years,
            interest_earned,
            maturity_amount,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        result = {
            "principal": principal,
            "rate": rate,
            "years": years,
            "interest": interest_earned,
            "maturity": maturity_amount
        }

    return render_template(
        "fd_calculator.html",
        result=result
    )
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


    # Current article
    cur.execute(
        """
        SELECT *
        FROM articles
        WHERE slug = %s
        """,
        (slug,)
    )

    article = cur.fetchone()


    if article is None:
        conn.close()
        return "Article not found", 404



    # -----------------------------------
    # Find related articles
    # -----------------------------------

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



    return render_template(
        'view_article.html',
        article=article,
        related_articles=related_articles

    )

@app.route("/disclaimer")
def disclaimer():
    return render_template("disclaimer.html")

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
            <lastmod>{str(article['created_at']).split(' ')[0]}</lastmod>
            <changefreq>monthly</changefreq>
            <priority>0.8</priority>
        </url>
        """)

    xml.append("</urlset>")

    return Response("\n".join(xml), mimetype="application/xml")

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

    pdf_path = "financial_report.pdf"

    generate_financial_report(
        pdf_path,
        user,
        data
    )

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name="SmartPlan_Finance_Report.pdf"
    )
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=False
    )