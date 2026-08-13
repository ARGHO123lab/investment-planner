from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm


# ============================================================
# SMARTPLAN FINANCE — MASTER FAQ PDF GENERATOR
# ============================================================

OUTPUT_FILE = "financial_guide.pdf"


def create_faq_pdf():

    doc = SimpleDocTemplate(
        OUTPUT_FILE,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    styles = getSampleStyleSheet()

    # --------------------------------------------------------
    # BRAND COLORS
    # --------------------------------------------------------

    gold = colors.HexColor("#B8860B")
    brown = colors.HexColor("#5D4037")
    dark = colors.HexColor("#222222")
    muted = colors.HexColor("#666666")

    # --------------------------------------------------------
    # CUSTOM STYLES
    # --------------------------------------------------------

    title_style = ParagraphStyle(
        "SPFTitle",
        parent=styles["Title"],
        fontSize=24,
        leading=28,
        textColor=gold,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=10.5,
        leading=15,
        textColor=muted,
        alignment=TA_CENTER,
        spaceAfter=16
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading1"],
        fontSize=16,
        leading=20,
        textColor=gold,
        fontName="Helvetica-Bold",
        spaceBefore=16,
        spaceAfter=9
    )

    question_style = ParagraphStyle(
        "Question",
        parent=styles["Heading2"],
        fontSize=11.5,
        leading=15,
        textColor=brown,
        fontName="Helvetica-Bold",
        spaceBefore=10,
        spaceAfter=4
    )

    answer_style = ParagraphStyle(
        "Answer",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=14,
        textColor=dark,
        leftIndent=10,
        spaceAfter=8
    )

    note_style = ParagraphStyle(
        "Note",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=12,
        textColor=muted,
        leftIndent=10,
        spaceBefore=4,
        spaceAfter=8
    )

    # ========================================================
    # FAQ CONTENT
    # ========================================================

    sections = [

        # ====================================================
        # 1. BUDGETING
        # ====================================================

        (
            "Budgeting & Money Management",
            [

                (
                    "What is a budget, and why does it matter?",
                    "A budget maps expected income against planned spending over a set period, "
                    "usually a month. It turns intentions such as “save more” into specific, "
                    "trackable numbers and creates a foundation for saving, investing and debt management."
                ),

                (
                    "What is the 50/30/20 rule, and how flexible is it?",
                    "It is a simple budgeting framework that allocates roughly 50% of take-home "
                    "income to needs, 30% to wants and 20% to savings and debt repayment. "
                    "It is a starting framework, not a law. Housing costs, debt, family responsibilities "
                    "and goals may require a different split."
                ),

                (
                    "How should I start if I have never made a budget?",
                    "Start with actual take-home income and recent spending. Separate needs, wants, "
                    "debt payments, savings and investments, then make one or two realistic changes "
                    "rather than trying to redesign everything at once."
                ),

            ]
        ),

        # ====================================================
        # 2. SAVING / EMERGENCY FUND
        # ====================================================

        (
            "Saving, Emergency Funds & Inflation",
            [

                (
                    "Why is an emergency fund considered essential?",
                    "An emergency fund is a liquid reserve for unexpected expenses or income disruptions. "
                    "A commonly used planning range is several months of essential expenses, but the "
                    "appropriate amount depends on job stability, dependants, insurance, debt and other circumstances."
                ),

                (
                    "How exactly does inflation erode personal wealth?",
                    "Inflation raises the price of goods and services over time, reducing what a fixed "
                    "amount of money can buy. If your money grows more slowly than inflation, its purchasing "
                    "power can decline even if the account balance increases."
                ),

                (
                    "Should emergency money be invested for higher returns?",
                    "The primary purpose of an emergency fund is availability and stability, not maximum growth. "
                    "The appropriate vehicle should therefore be liquid and consistent with the user's access and risk needs."
                ),

            ]
        ),

        # ====================================================
        # 3. INVESTING
        # ====================================================

        (
            "Investing Fundamentals",
            [

                (
                    "How does compounding actually accelerate growth?",
                    "Compounding occurs when investment returns are reinvested and future returns can then "
                    "be earned on a larger base. The effect generally becomes more powerful over longer periods, "
                    "making time a major advantage for long-term investors."
                ),

                (
                    "What is an SIP and who is it suited for?",
                    "A Systematic Investment Plan (SIP) is a method of investing a fixed amount at regular "
                    "intervals, commonly in mutual funds. It can help people build a disciplined contribution "
                    "habit rather than relying on a single investment decision."
                ),

                (
                    "What does diversification actually protect you from?",
                    "Diversification spreads exposure across investments, sectors or asset classes so that one "
                    "holding has less influence on the whole portfolio. It can reduce concentration risk, but "
                    "it cannot eliminate investment risk or guarantee returns."
                ),

                (
                    "How is asset allocation different from diversification?",
                    "Asset allocation is the higher-level decision about how much of a portfolio is placed in "
                    "broad asset classes such as equity and debt. Diversification spreads exposure within or "
                    "across those allocations. The appropriate mix depends on goals, time horizon and risk capacity."
                ),

                (
                    "How reliable is the Rule of 72?",
                    "The Rule of 72 is a quick estimate for the time needed to double money: divide 72 by an "
                    "assumed annual rate. At 8%, for example, it suggests roughly nine years. It is a shortcut "
                    "rather than an exact forecast and is less suitable for irregular or highly volatile returns."
                ),

            ]
        ),

        # ====================================================
        # 4. MUTUAL FUNDS / EQUITY / DEBT
        # ====================================================

        (
            "Mutual Funds, Equity & Debt",
            [

                (
                    "What exactly happens to your money inside a mutual fund?",
                    "A mutual fund pools money from investors and invests according to its stated strategy. "
                    "Investors receive units representing their share of the fund, and unit value changes with "
                    "the underlying portfolio, expenses and other applicable factors."
                ),

                (
                    "How is an index fund different from an actively managed fund?",
                    "An index fund generally seeks to track a specified market index rather than select investments "
                    "to outperform it. An actively managed fund uses a manager or management team to select investments "
                    "according to its strategy. Costs, tracking and performance can differ."
                ),

                (
                    "Why can't you get high returns without taking on risk?",
                    "Higher potential returns generally come with greater uncertainty. There is no investment that "
                    "can simultaneously guarantee high returns, low risk and immediate liquidity in every market environment."
                ),

                (
                    "What are the real risks and rewards of equity investing?",
                    "Equity represents ownership in a company. It can provide long-term growth potential, but prices "
                    "can fall substantially and individual companies can perform poorly. Suitability depends on the "
                    "investor's horizon, goals and ability to tolerate losses."
                ),

                (
                    "How do debt investments differ from equity in practice?",
                    "Debt investments generally represent lending to a borrower in exchange for interest and repayment "
                    "terms. Their risk and return characteristics differ from equity, and actual safety, liquidity and "
                    "return depend on the specific instrument and issuer."
                ),

            ]
        ),

        # ====================================================
        # 5. RETIREMENT
        # ====================================================

        (
            "Retirement & Financial Independence",
            [

                (
                    "Why does starting retirement planning early matter so much?",
                    "Starting early gives contributions and potential returns more time to compound. This can reduce "
                    "the contribution burden required later, although actual outcomes depend on savings, returns, "
                    "inflation, taxes, fees and retirement spending."
                ),

                (
                    "How do you calculate the retirement corpus you'll need?",
                    "Estimate retirement spending, account for inflation and the expected retirement period, consider "
                    "other income and existing assets, and model a suitable return assumption. A retirement calculator "
                    "can perform this calculation, but the result remains an estimate."
                ),

                (
                    "Does retiring early require a higher savings rate?",
                    "Usually, early retirement requires more financial capacity because there are fewer earning years "
                    "and potentially more years for the portfolio to fund. The exact savings rate depends on target "
                    "retirement age, spending, assets, income and assumptions."
                ),

                (
                    "What is FIRE?",
                    "FIRE stands for Financial Independence, Retire Early. The broad idea is to build enough financial "
                    "assets and sustainable cash flow that employment becomes optional earlier than traditional retirement. "
                    "There is no single required savings rate or investment strategy."
                ),

            ]
        ),

        # ====================================================
        # 6. PPF / NPS
        # ====================================================

        (
            "PPF, NPS & Long-Term Saving",
            [

                (
                    "What makes PPF attractive for long-term savers?",
                    "The Public Provident Fund (PPF) is a government-backed long-term savings scheme with a prescribed "
                    "tenure and government-notified interest rate. Its tax treatment and rules make it relevant to "
                    "long-term planning, but users should verify current rates and rules from official sources before acting."
                ),

                (
                    "How does the National Pension System (NPS) work?",
                    "NPS is a market-linked retirement system in which contributions are invested through permitted asset "
                    "classes and the account follows applicable withdrawal and exit rules. Tax treatment and exit provisions "
                    "depend on the applicable rules and subscriber category."
                ),

                (
                    "Is NPS tax-efficient?",
                    "NPS can provide tax benefits subject to applicable Income Tax Act provisions and limits. "
                    "Because tax rules can change, users should verify current provisions before making a decision."
                ),

            ]
        ),

        # ====================================================
        # 7. TAX / INSURANCE / DEBT
        # ====================================================

        (
            "Tax, Insurance, Debt & Credit",
            [

                (
                    "What's the legal difference between tax avoidance and tax evasion?",
                    "Tax planning uses provisions allowed by law to organise finances and reduce tax liability. "
                    "Tax evasion involves illegal concealment, misreporting or falsification. SPF supports lawful, "
                    "transparent financial planning."
                ),

                (
                    "Why do financial planners often discuss term life insurance for income protection?",
                    "Term insurance is primarily protection: it can provide a specified death benefit during the policy "
                    "term in exchange for a premium. Whether it is appropriate depends on dependants, liabilities, "
                    "income-replacement needs, existing cover and policy terms."
                ),

                (
                    "Should you clear debt before you start investing?",
                    "There is no universal answer. Compare the debt's interest cost, risk and repayment terms with the "
                    "purpose and expected risk of the investment. High-cost revolving debt deserves particular attention "
                    "because its cost can be substantial."
                ),

                (
                    "What actually determines your credit score?",
                    "Credit scores are based on information in a person's credit history. Factors can include repayment "
                    "behaviour, credit utilisation, credit history, types of credit and recent credit activity. "
                    "The exact scoring model and weighting depend on the bureau and scoring system."
                ),

                (
                    "What's the real cost of paying only the minimum on a credit card?",
                    "Paying only the minimum can leave a balance outstanding, potentially leading to interest and "
                    "extending the repayment period. Users should always check their card's current terms and statement."
                ),

            ]
        ),

        # ====================================================
        # 8. MARKETS / RISK
        # ====================================================

        (
            "Markets, Risk & Behaviour",
            [

                (
                    "How does rupee-cost averaging reduce timing pressure?",
                    "Investing a fixed amount at regular intervals means more units are purchased when prices are lower "
                    "and fewer when prices are higher. It can reduce the need to predict the perfect entry point, but "
                    "it does not guarantee a profit or protect against market declines."
                ),

                (
                    "What does volatility actually measure?",
                    "Volatility describes the magnitude and frequency of price movements over a period. Higher volatility "
                    "means greater short-term price variation; it does not by itself determine whether an investment is good or bad."
                ),

                (
                    "What matters more for long-term wealth: timing the market or time in the market?",
                    "Trying to predict short-term market highs and lows is difficult. A disciplined long-term approach "
                    "can reduce the importance of any single entry point, but the appropriate strategy still depends on "
                    "goals, risk and circumstances."
                ),

                (
                    "Why can a high-return investment still be unsuitable?",
                    "An investment can have attractive historical or projected returns while still being unsuitable because "
                    "of volatility, liquidity limits, concentration, fees, taxes or the investor's time horizon. "
                    "Suitability is broader than return."
                ),

            ]
        ),

        # ====================================================
        # 9. SMARTPLAN FINANCE
        # ====================================================

        (
            "SmartPlan Finance Tools & Content",
            [

                (
                    "What is SmartPlan Finance?",
                    "SmartPlan Finance (SPF) is a personal-finance education platform focused on practical explanations, "
                    "financial calculators, planning tools and long-term wealth-building education."
                ),

                (
                    "Who is SmartPlan Finance for?",
                    "SPF is designed for people who want personal-finance concepts explained clearly, including beginners "
                    "and users who want to model financial scenarios using calculators and planning tools."
                ),

                (
                    "What are SPF calculators designed to do?",
                    "SPF calculators turn user-provided assumptions into estimates that make financial scenarios easier "
                    "to understand. They are planning tools, not guarantees of future outcomes."
                ),

                (
                    "What is the SPF Personal Financial Planner?",
                    "The Personal Financial Planner is a structured tool intended to help users organise financial information, "
                    "identify goals and develop a practical financial roadmap."
                ),

                (
                    "What topics do SPF articles cover?",
                    "SPF content can cover budgeting, saving, investing, SIPs, mutual funds, retirement, salary and income "
                    "planning, taxes, emergency funds, wealth building and other personal-finance topics."
                ),

                (
                    "Why does SPF provide official sources on articles?",
                    "Official sources help readers verify important facts and explore primary information directly. "
                    "This is especially important for tax rules, regulations, rates and other information that can change."
                ),

                (
                    "Can SPF tell me exactly what I should invest in?",
                    "SPF can explain concepts, compare approaches and model scenarios, but general educational content cannot "
                    "account for every individual's circumstances. It should not be treated as personalised investment advice."
                ),

                (
                    "Are SPF calculator results guaranteed?",
                    "No. Results are estimates based on the assumptions entered. Actual outcomes can differ because returns, "
                    "inflation, taxes, fees, contribution timing and other conditions can change."
                ),

            ]
        ),

        # ====================================================
        # 10. TRUST / PRIVACY
        # ====================================================

        (
            "Responsible Use, Privacy & Trust",
            [

                (
                    "Does SPF need my personal financial information just to read an article?",
                    "No. General article reading does not require a user to disclose their complete financial situation."
                ),

                (
                    "Should I enter sensitive information into a calculator?",
                    "Only provide information that the particular tool requires and that you are comfortable providing. "
                    "Never enter passwords, banking credentials, card PINs, one-time passwords or other authentication "
                    "secrets into an educational calculator."
                ),

                (
                    "Can SPF articles become outdated?",
                    "Yes. Tax rules, regulations, rates, product features and market conditions can change. "
                    "Time-sensitive information should be checked against current official sources before action is taken."
                ),

                (
                    "Can an SPF article or FAQ replace professional advice?",
                    "No. SPF provides general educational information. Personalised financial, tax, legal or insurance "
                    "decisions may require advice from an appropriately qualified professional."
                ),

                (
                    "What should I do before making a significant financial decision?",
                    "Understand the goal, time horizon, liquidity needs, risks, costs and taxes; verify current information "
                    "from authoritative sources; and consider professional advice where the decision is material or complex."
                ),

            ]
        ),

    ]

    # ========================================================
    # BUILD DOCUMENT
    # ========================================================

    story = []

    story.append(
        Paragraph(
            "SmartPlan Finance FAQ Guide",
            title_style
        )
    )

    story.append(
        Paragraph(
            "A practical, plain-English reference for personal finance, investing, planning and wealth building",
            subtitle_style
        )
    )

    story.append(
        Paragraph(
            "<b>Built from the original SmartPlan Finance FAQ.</b> "
            "The original questions and core explanations have been retained as the foundation, "
            "while additional SPF-specific and responsible-use questions have been added.",
            note_style
        )
    )

    # --------------------------------------------------------
    # FAQ SECTIONS
    # --------------------------------------------------------

    for section_name, questions in sections:

        story.append(
            Paragraph(
                section_name,
                section_style
            )
        )

        for question, answer in questions:

            story.append(
                KeepTogether(
                    [
                        Paragraph(
                            "Q: " + question,
                            question_style
                        ),

                        Paragraph(
                            answer,
                            answer_style
                        )
                    ]
                )
            )

    # ========================================================
    # DISCLAIMER
    # ========================================================

    story.append(
        Paragraph(
            "Important Disclaimer",
            section_style
        )
    )

    story.append(
        Paragraph(
            "<b>Educational purpose only.</b> SmartPlan Finance provides general financial "
            "education and planning tools. Nothing in this guide should be interpreted as "
            "personalised investment, financial, tax, legal or insurance advice, or as a "
            "guarantee of any financial outcome. Financial products, laws, tax rules, rates "
            "and regulations can change. Readers should verify current information from "
            "authoritative sources and consider their own circumstances before acting.",
            answer_style
        )
    )

    # ========================================================
    # OFFICIAL SOURCE NOTE
    # ========================================================

    story.append(
        Paragraph(
            "Official-Source Note",
            section_style
        )
    )

    story.append(
        Paragraph(
            "For time-sensitive topics such as NPS, tax treatment, credit-card rules, "
            "rates and regulatory requirements, readers should consult the latest applicable "
            "official material. This guide deliberately avoids presenting changing rates "
            "or thresholds as permanent facts.",
            answer_style
        )
    )

    story.append(
        Spacer(
            1,
            8
        )
    )

    story.append(
        Paragraph(
            "SmartPlan Finance • Master FAQ • August 2026",
            note_style
        )
    )

    # ========================================================
    # PAGE NUMBER
    # ========================================================

    def add_page_number(canvas, doc):

        canvas.saveState()

        canvas.setFont(
            "Helvetica",
            8
        )

        canvas.setFillColor(
            muted
        )

        canvas.drawCentredString(
            A4[0] / 2,
            9 * mm,
            f"SmartPlan Finance FAQ Guide  •  Page {doc.page}"
        )

        canvas.restoreState()

    # ========================================================
    # CREATE PDF
    # ========================================================

    doc.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number
    )

    print(
        f"{OUTPUT_FILE} created successfully!"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    create_faq_pdf()