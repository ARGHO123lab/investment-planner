# wellness.py

LITERACY_QUESTIONS = [
    {
        "id": "q1",
        "question": "What does SIP stand for?",
        "options": ["Systematic Investment Plan", "Special Interest Plan", "Stock Investment Program", "Savings Insurance Plan"],
        "correct": "Systematic Investment Plan"
    },
    {
        "id": "q2",
        "question": "The market drops 20% while you're doing a long-term SIP. What should you generally do?",
        "options": ["Stop the SIP immediately", "Continue the SIP as planned", "Withdraw everything", "Switch to Fixed Deposit"],
        "correct": "Continue the SIP as planned"
    },
    {
        "id": "q3",
        "question": "What is an emergency fund mainly used for?",
        "options": ["Buying stocks on dips", "Unexpected expenses like job loss or medical bills", "Paying for vacations", "Investing in mutual funds"],
        "correct": "Unexpected expenses like job loss or medical bills"
    },
    {
        "id": "q4",
        "question": "Which has the shortest lock-in period among common tax-saving options?",
        "options": ["PPF (15 years)", "NPS (till retirement)", "ELSS (3 years)", "Fixed Deposit (5 years)"],
        "correct": "ELSS (3 years)"
    },
    {
        "id": "q5",
        "question": "What does 'diversification' mean in investing?",
        "options": ["Investing all your money in one company", "Spreading investments across different assets to reduce risk", "Only investing in gold", "Timing the market perfectly"],
        "correct": "Spreading investments across different assets to reduce risk"
    },
    {
        "id": "q6",
        "question": "What is compound interest?",
        "options": ["Interest paid only on the original amount", "Interest earned on both the principal and previously earned interest", "A one-time bonus from your bank", "A type of loan"],
        "correct": "Interest earned on both the principal and previously earned interest"
    },
    {
        "id": "q7",
        "question": "What is the 50-30-20 rule generally used for?",
        "options": ["Tax filing deadlines", "Budgeting income into needs, wants, and savings", "Calculating loan interest", "Retirement age planning"],
        "correct": "Budgeting income into needs, wants, and savings"
    },
    {
        "id": "q8",
        "question": "What does 'inflation' do to the value of money over time?",
        "options": ["Increases its purchasing power", "Has no effect", "Decreases its purchasing power", "Doubles it every year"],
        "correct": "Decreases its purchasing power"
    }
]


def calculate_health_score(income, expense, savings, emergency_fund, debt):
    """Returns a health score out of 100 based on basic financial ratios."""

    if income <= 0:
        return 0

    savings_rate = (savings / income) * 100
    debt_to_income = (debt / income) * 100 if debt else 0
    emergency_months = (emergency_fund / expense) if expense > 0 else 0

    score = 0

    # Savings rate - up to 40 points
    score += min(savings_rate * 1.3, 40)

    # Emergency fund coverage - up to 30 points (6 months = full marks)
    score += min((emergency_months / 6) * 30, 30)

    # Debt-to-income - up to 30 points (lower debt = higher score)
    if debt_to_income == 0:
        score += 30
    elif debt_to_income < 20:
        score += 22
    elif debt_to_income < 40:
        score += 12
    else:
        score += 4

    return min(int(score), 100)


def calculate_literacy_score(answers):
    """answers = dict like {'q1': 'Systematic Investment Plan', ...}"""
    correct_count = 0

    for q in LITERACY_QUESTIONS:
        if answers.get(q["id"]) == q["correct"]:
            correct_count += 1

    return correct_count, len(LITERACY_QUESTIONS)


def get_health_breakdown(income, expense, savings, emergency_fund, debt):
    """Returns plain-English notes about strengths/weaknesses for the AI prompt."""

    notes = []

    savings_rate = (savings / income) * 100 if income > 0 else 0
    emergency_months = (emergency_fund / expense) if expense > 0 else 0
    debt_to_income = (debt / income) * 100 if income > 0 else 0

    notes.append(f"Savings rate: {savings_rate:.1f}% of income")
    notes.append(f"Emergency fund covers: {emergency_months:.1f} months of expenses")
    notes.append(f"Debt-to-income ratio: {debt_to_income:.1f}%")

    return notes