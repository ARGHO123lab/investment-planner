from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

def create_faq_pdf():
    doc = SimpleDocTemplate("financial_guide.pdf", pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle('Title', fontSize=24, textColor=colors.HexColor("#B8860B"), 
                                 fontName="Helvetica-Bold", alignment=1, spaceAfter=20)
    q_style = ParagraphStyle('Question', fontSize=14, textColor=colors.HexColor("#5D4037"), 
                             fontName="Helvetica-Bold", spaceBefore=15, spaceAfter=5)
    a_style = ParagraphStyle('Answer', fontSize=12, textColor=colors.black, 
                             fontName="Helvetica", spaceAfter=10, leftIndent=20)

    story = [Paragraph("SmartPlan Finance FAQ Guide", title_style)]

    faqs = [
        ("What is a budget?", "A budget is a financial plan that tracks your income and expenses over a specific period, helping you control spending and save for goals."),
        ("What is the '50/30/20' rule?", "It’s a budgeting framework: 50% of income for Needs, 30% for Wants, and 20% for Savings and Debt Repayment."),
        ("Why is an emergency fund vital?", "It provides a liquid safety net (typically 6 months of expenses) to handle job loss or medical emergencies without accumulating debt."),
        ("How does inflation affect personal wealth?", "Inflation decreases the purchasing power of money over time; if your investment returns don't exceed the inflation rate, your real wealth shrinks."),
        ("What is the difference between assets and liabilities?", "Assets put money in your pocket (e.g., stocks, real estate), while liabilities take money out (e.g., high-interest credit card debt)."),
        ("What is compounding?", "It is the process where your investment returns generate their own earnings, leading to exponential growth over long periods."),
        ("What is an SIP?", "A Systematic Investment Plan is a method of investing a fixed amount regularly into mutual funds, minimizing market timing risks."),
        ("What is diversification?", "It is the strategy of spreading investments across different asset classes to minimize overall risk."),
        ("What is asset allocation?", "It is the practice of dividing an investment portfolio among different asset categories based on risk tolerance and time horizon."),
        ("What is the 'Rule of 72'?", "A formula to estimate the time required to double an investment (72 / Annual Interest Rate = Years to double)."),
        ("What is a mutual fund?", "A pooled investment vehicle where money from many investors is managed by professionals and invested in securities."),
        ("What is an Index Fund?", "A fund designed to mirror the performance of a specific market index."),
        ("What is the risk-return trade-off?", "The principle that higher potential returns usually come with higher risk."),
        ("What is an Equity investment?", "Investing in shares of companies, which offers potential for high growth but involves market risk."),
        ("What is Debt investment?", "Investing in fixed-income instruments like bonds or FDs, which generally offer lower, predictable returns."),
        ("When should one start retirement planning?", "As early as possible to maximize the effect of compounding."),
        ("How is a retirement corpus calculated?", "By estimating your post-retirement monthly expenses, adjusting for inflation, and determining the lump sum needed."),
        ("What is a Public Provident Fund (PPF)?", "A government-backed long-term savings scheme offering tax benefits and guaranteed returns."),
        ("What is a National Pension System (NPS)?", "A voluntary, market-linked defined contribution retirement scheme."),
        ("Does an early retirement require a higher savings rate?", "Yes, because you have fewer years to accumulate capital and need your funds to last longer."),
        ("Difference between tax evasion and tax avoidance?", "Avoidance is legal tax minimization; evasion is the illegal non-payment of taxes."),
        ("What is the benefit of a Term Life Insurance?", "It provides a large death benefit to your family at a low cost, focusing purely on protection."),
        ("Should you pay off debt before investing?", "If the debt interest rate is higher than expected investment returns, pay off the debt first."),
        ("What is credit score?", "A numerical representation of your creditworthiness, based on your history of borrowing and repaying debt."),
        ("How does a Credit Card work?", "It allows you to borrow money up to a limit, which must be repaid; high interest applies if not paid in full."),
        ("What is dollar-cost averaging?", "Investing a fixed dollar amount at regular intervals, lowering the average cost per share over time."),
        ("What is volatility?", "The degree of variation in the trading price of a security over time."),
        ("What is the 'FIRE' movement?", "Financial Independence, Retire Early—a movement dedicated to extreme saving and investing."),
        ("Why are FDs considered low risk?", "Because Fixed Deposits offer a guaranteed interest rate regardless of market conditions."),
        ("What is the most important factor in long-term wealth creation?", "Consistency and time in the market (discipline), rather than timing the market.")
    ]

    for q, a in faqs:
        story.append(Paragraph(f"Q: {q}", q_style))
        story.append(Paragraph(a, a_style))

    doc.build(story)
    print("financial_guide.pdf created successfully!")

if __name__ == "__main__":
    create_faq_pdf()