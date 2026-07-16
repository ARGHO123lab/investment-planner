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
    (
        "What is a budget, and why does it matter?",
        "A budget is a plan that maps your expected income against your planned spending over a set period, usually a month. "
        "It matters because it turns vague intentions like 'save more' into specific, trackable numbers, and it's the "
        "foundation every other financial decision — saving, investing, debt payoff — is built on."
    ),
    (
        "What is the 50/30/20 rule, and how flexible is it?",
        "It's a simple budgeting split: roughly 50% of take-home income goes to Needs (rent, groceries, utilities), 30% to "
        "Wants (dining out, entertainment, subscriptions), and 20% to Savings and debt repayment. It's a starting template, "
        "not a strict law — someone with high rent or a big loan EMI may need to adjust the ratios, for example shifting to "
        "60/20/20, until their situation stabilizes."
    ),
    (
        "Why is an emergency fund considered essential?",
        "An emergency fund is a cash reserve, typically covering 3 to 6 months of essential expenses, kept in a liquid, "
        "low-risk account. Its job isn't to grow your wealth — it's to absorb shocks like a job loss or medical bill without "
        "forcing you to sell investments at a bad time or take on high-interest debt."
    ),
    (
        "How exactly does inflation erode personal wealth?",
        "Inflation raises the price of goods and services over time, which means a fixed sum of money buys less in the "
        "future than it does today. If your savings sit in an account earning less interest than the inflation rate, "
        "your money's real, inflation-adjusted value is shrinking even as the number on your statement stays the same or grows slowly."
    ),
    (
        "What's the practical difference between an asset and a liability?",
        "An asset is something that puts money in your pocket over time or holds value you can convert to cash, such as "
        "stocks, mutual funds, or property that appreciates. A liability takes money out of your pocket on an ongoing basis, "
        "like credit card debt or a personal loan. The distinction matters because two people with the same net worth can "
        "have very different financial health depending on this mix."
    ),
    (
        "How does compounding actually accelerate growth?",
        "Compounding happens when the returns your investment earns are reinvested, so future returns are calculated on a "
        "larger base each time. The effect is small in early years but accelerates sharply over long horizons — which is why "
        "starting even a small SIP in your 20s can outperform a much larger one started in your 40s, purely due to extra time in the market."
    ),
    (
        "What is an SIP and who is it suited for?",
        "A Systematic Investment Plan (SIP) lets you invest a fixed amount into a mutual fund at regular intervals, usually "
        "monthly, instead of investing a lump sum at one point in time. It suits salaried individuals with regular income "
        "because it builds a disciplined habit and averages out the purchase price across market ups and downs, reducing the "
        "risk of investing everything right before a downturn."
    ),
    (
        "What does diversification actually protect you from?",
        "Diversification means spreading money across different asset classes — equity, debt, gold, real estate — so that "
        "poor performance in one area doesn't sink your entire portfolio. It doesn't eliminate risk or guarantee returns, but "
        "it reduces the impact of any single investment or sector going badly wrong."
    ),
    (
        "How is asset allocation different from diversification?",
        "Diversification is about spreading risk within and across asset classes; asset allocation is the higher-level "
        "decision of how much of your total portfolio goes into each class in the first place — for example, 70% equity and "
        "30% debt for a 30-year-old, shifting to 40% equity and 60% debt closer to retirement. Allocation is driven mainly by "
        "your risk tolerance and time horizon."
    ),
    (
        "How reliable is the Rule of 72 for estimating investment growth?",
        "The Rule of 72 estimates how many years it takes to double an investment by dividing 72 by the annual rate of "
        "return — for example, at 8% annual returns, money roughly doubles in 9 years. It's a quick mental-math tool, not an "
        "exact formula, and works best for moderate, steady interest rates rather than highly volatile returns."
    ),
    (
        "What exactly happens to your money inside a mutual fund?",
        "A mutual fund pools money from many investors and a professional fund manager invests that pool in a basket of "
        "securities — stocks, bonds, or a mix — according to the fund's stated strategy. You own units of the fund "
        "proportional to your investment, and the fund's Net Asset Value (NAV) rises or falls based on how the underlying "
        "holdings perform."
    ),
    (
        "How is an index fund different from an actively managed fund?",
        "An index fund simply tracks a market index like the Nifty 50 or Sensex, buying the same stocks in the same "
        "proportion, so its returns closely mirror the index. An actively managed fund has a manager trying to beat the "
        "index through stock selection, which usually comes with higher fees and no guarantee of outperformance."
    ),
    (
        "Why can't you get high returns without taking on risk?",
        "The risk-return trade-off reflects a basic market reality: investors demand higher potential compensation for "
        "taking on greater uncertainty. Low-risk instruments like fixed deposits offer modest, predictable returns because "
        "the capital is safe, while equities offer higher long-term potential precisely because their short-term value can swing significantly."
    ),
    (
        "What are the real risks and rewards of equity investing?",
        "Equity means buying ownership shares in a company. Over long periods, equities have historically outpaced "
        "inflation and other asset classes, but in the short term they can be highly volatile, and there's no guarantee "
        "of returns — some companies underperform or fail entirely, so equity exposure should generally match a longer investment horizon."
    ),
    (
        "How do debt investments differ from equity in practice?",
        "Debt investments — bonds, fixed deposits, debt mutual funds — involve lending money to a government or company in "
        "exchange for regular interest payments and return of principal. Returns are typically lower than equity but far "
        "more predictable, making debt instruments useful for capital preservation and shorter time horizons rather than aggressive growth."
    ),
    (
        "Why does starting retirement planning early matter so much?",
        "Starting early gives compounding more time to work, which means you can reach the same retirement corpus with "
        "smaller monthly contributions than someone who starts a decade later. Delaying retirement planning by even five "
        "years often requires disproportionately larger contributions later to catch up."
    ),
    (
        "How do you actually calculate the retirement corpus you'll need?",
        "Start by estimating your current monthly expenses, project them forward to your retirement age adjusting for "
        "inflation, then calculate the lump sum that could sustainably fund those inflation-adjusted expenses for your "
        "expected retirement duration — factoring in the returns you expect the corpus itself to keep earning. A retirement calculator "
        "handles this compounding math automatically, since doing it by hand across 20-30 years is error-prone."
    ),
    (
        "What makes the Public Provident Fund (PPF) attractive for long-term savers?",
        "PPF is a government-backed savings scheme with a 15-year lock-in, offering a fixed, government-set interest rate "
        "and full tax exemption on contributions, interest earned, and maturity proceeds under the EEE tax status. Its "
        "safety and tax efficiency make it a common core holding for conservative, long-term goals like retirement."
    ),
    (
        "How does the National Pension System (NPS) work?",
        "NPS is a voluntary, market-linked retirement scheme where contributions are invested across a mix of equity, "
        "corporate debt, and government bonds based on your chosen allocation or age-based auto-allocation. It offers "
        "additional tax benefits beyond standard deduction limits, but part of the maturity corpus must be used to purchase an annuity, which affects liquidity at retirement."
    ),
    (
        "Does retiring early really require a much higher savings rate?",
        "Yes — retiring early compresses your earning years while extending the years your corpus must support, so you "
        "need to save a significantly higher percentage of income than someone retiring at the standard age. Many early "
        "retirement plans target savings rates of 40-50% or more of income specifically to close this gap."
    ),
    (
        "What's the legal line between tax avoidance and tax evasion?",
        "Tax avoidance uses legal provisions — deductions, exemptions, approved investment schemes — to legitimately reduce "
        "your tax liability. Tax evasion involves illegally concealing income or falsifying records to avoid paying tax owed. "
        "The first is standard financial planning; the second carries legal penalties."
    ),
    (
        "Why do financial planners recommend term life insurance over other policies?",
        "Term insurance provides a large death benefit to your dependents for a relatively low premium because it's pure "
        "protection with no investment or savings component. This makes it far more cost-effective for covering income "
        "replacement needs than investment-linked insurance plans, which bundle in higher costs and typically lower effective returns."
    ),
    (
        "Should you clear debt before you start investing?",
        "Compare the interest rate on your debt to the return you realistically expect from investing. If a loan or "
        "credit card is charging more than your expected investment return — which is often the case with credit card debt at "
        "36%+ annually — paying it off first is effectively a guaranteed, risk-free return equal to that interest rate."
    ),
    (
        "What actually determines your credit score?",
        "A credit score is a numerical summary of your creditworthiness, calculated mainly from your repayment history, "
        "credit utilization (how much of your available credit you're using), length of credit history, and the mix of "
        "credit types you hold. Lenders use it to price and approve loans, so missed payments or high utilization can affect approval odds and interest rates for years."
    ),
    (
        "What's the real cost of only paying the minimum on a credit card?",
        "A credit card lets you borrow up to a set limit and repay later, but if you carry a balance past the due date, "
        "interest — often 30-45% annually in India — applies to the outstanding amount, and paying only the minimum due "
        "extends repayment for years while interest compounds on the remainder. Paying the full statement balance each cycle avoids this entirely."
    ),
    (
        "How does dollar-cost averaging reduce timing risk?",
        "Dollar-cost (or rupee-cost) averaging means investing a fixed amount at regular intervals regardless of market "
        "level, so you automatically buy more units when prices are low and fewer when prices are high. Over time this "
        "smooths out your average purchase cost and removes the pressure of trying to time market entry perfectly."
    ),
    (
        "What does 'volatility' actually measure?",
        "Volatility measures how much and how quickly a security's price swings over a given period — high volatility "
        "means large, frequent price movements, while low volatility means relatively stable pricing. It's a measure of "
        "short-term uncertainty, not necessarily of long-term quality, since some volatile assets still deliver strong long-term returns."
    ),
    (
        "What does the FIRE movement actually involve day to day?",
        "FIRE (Financial Independence, Retire Early) centers on saving a very high percentage of income, often 50% or "
        "more, and investing aggressively so that a portfolio can sustainably cover living expenses well before traditional "
        "retirement age. In practice this usually means deliberately minimizing lifestyle inflation while income grows, rather than any single investment trick."
    ),
    (
        "Why are fixed deposits considered low-risk if returns are modest?",
        "Fixed Deposits lock in a guaranteed interest rate for a set tenure, and the principal is protected regardless of "
        "market movements, with bank FDs additionally covered by deposit insurance up to a limit. The trade-off for that "
        "safety is a return that often barely keeps pace with inflation, which is why FDs work better for short-term goals or capital protection than long-term wealth building."
    ),
    (
        "What matters more for long-term wealth: timing the market or time in the market?",
        "Consistently investing over a long horizon and staying invested through market cycles has historically "
        "outperformed attempts to predict short-term highs and lows, largely because missing even a handful of the market's "
        "best days can significantly drag down long-term returns. Discipline and duration tend to matter more than any individual entry or exit decision."
    ),
]

    for q, a in faqs:
        story.append(Paragraph(f"Q: {q}", q_style))
        story.append(Paragraph(a, a_style))

    doc.build(story)
    print("financial_guide.pdf created successfully!")

if __name__ == "__main__":
    create_faq_pdf()