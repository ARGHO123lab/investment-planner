from datetime import datetime

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image
)

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import os

###################################################
# PDF FOOTER
###################################################

def add_page_number(canvas, doc):

    canvas.saveState()

    canvas.setFont(
        "Helvetica",
        9
    )

    canvas.setFillColor(
        colors.grey
    )

    page_number = canvas.getPageNumber()

    canvas.drawCentredString(
        300,
        20,
        f"SmartPlan Finance AI | Page {page_number}"
    )

    canvas.restoreState()
def generate_financial_report(output_path, user, data):

    doc = SimpleDocTemplate(
    output_path,
    title="SmartPlan Finance AI Wealth Report",
    author="SmartPlan Finance",
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    title = ParagraphStyle(
    "CustomTitle",
    parent=styles["Title"],
    alignment=TA_CENTER,
    fontSize=28,
    leading=35,
    textColor=colors.HexColor("#B8860B")
)

    heading = styles["Heading1"]
    heading.textColor = colors.HexColor("#B8860B")

    subheading = styles["Heading2"]
    subheading.textColor = colors.HexColor("#444444")
    premium_text = ParagraphStyle(
    "PremiumText",
    parent=styles["BodyText"],
    alignment=TA_CENTER,
    fontSize=14,
    leading=22,
    textColor=colors.HexColor("#555555")
)
    

    normal = styles["BodyText"]

    story = []
       
    

    table_style = TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#B8860B")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),

        ("GRID",(0,0),(-1,-1),0.5,colors.grey),

        ("BACKGROUND",(0,1),(-1,-1),colors.whitesmoke),

        ("BOTTOMPADDING",(0,0),(-1,-1),8),

        ("TOPPADDING",(0,0),(-1,-1),8),

        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold")
    ])

    ###################################################
    # COVER PAGE
    ###################################################
    ###################################################
    # SMARTPLAN LOGO
    ###################################################

    logo_path = "static/images/logo.png"

    if os.path.exists(logo_path):

        logo = Image(
            logo_path,
            width=1.2*inch,
            height=1.2*inch
        )

        story.append(logo)

        story.append(
            Spacer(1,20)
        )
    story.append(Spacer(1,0.5*inch))

    story.append(
        Paragraph(
            "SMARTPLAN FINANCE",
            title
        )
    )

    story.append(Spacer(1,0.15*inch))

    story.append(
        Paragraph(
            "India's AI Powered Personal Finance Platform",
            subheading
        )
    )

    story.append(Spacer(1,0.60*inch))

    story.append(
        Paragraph(
            "<font size=24><b>AI WEALTH REPORT</b></font>",
            title
        )
    )

    story.append(Spacer(1,0.70*inch))

    story.append(
        Paragraph(
            f"<b>Prepared For</b><br/><br/>{user['name']}",
            styles["Heading2"]
        )
    )

    story.append(Spacer(1,0.40*inch))

    story.append(
        Paragraph(
            f"<b>Country :</b> {user['country']}",
            normal
        )
    )

    story.append(
        Paragraph(
            f"<b>Financial Health Score :</b> {data['score']} / 100",
            normal
        )
    )

    story.append(
        Paragraph(
            f"<b>Risk Profile :</b> {data['risk']}",
            normal
        )
    )
    from datetime import datetime
    

    
    story.append(Spacer(1,0.8*inch))

    if data["score"] >= 80:

        health = "🟢 Excellent Financial Health"

    elif data["score"] >= 60:

        health = "🟡 Good Financial Health"

    else:

        health = "🔴 Needs Improvement"

    story.append(
        Paragraph(
            health,
            styles["Heading2"]
        )
    )

    story.append(Spacer(1,1.1*inch))

    story.append(
        Paragraph(
            "<i>Plan Smart. Invest Smarter.</i>",
            styles["Italic"]
        )
    )

    story.append(
        Paragraph(
            "www.smartplanfinance.com<br/>"
"AI Powered Personal Wealth Intelligence Platform",
premium_text
        )
    )

    story.append(PageBreak())

    ###################################################
    # EXECUTIVE SUMMARY
    ###################################################

    story.append(
        Paragraph(
            "Executive Summary",
            heading
        )
    )

    story.append(Spacer(1,15))

    story.append(

        Paragraph(

            """
            This report provides an AI-powered overview of your
            current financial position based on your income,
            savings, expenses and investment profile.

            It highlights your financial strengths, identifies
            areas of improvement and provides personalized
            recommendations to help you build long-term wealth.
            """,

            normal

        )

    )

    story.append(Spacer(1,25))

    summary = [

        ["Metric","Value"],

        ["Monthly Income",
         f"₹ {data['income']:,.0f}"],

        ["Monthly Expenses",
         f"₹ {data['expense']:,.0f}"],

        ["Monthly Savings",
         f"₹ {data['savings']:,.0f}"],

        ["Financial Score",
         str(data["score"])],

        ["Risk Profile",
         data["risk"]]

    ]

    table = Table(

        summary,

        colWidths=[240,180]

    )

    table.setStyle(table_style)

    story.append(table)

    story.append(Spacer(1,25))
        ###################################################
    # FINANCIAL DASHBOARD
    ###################################################

    story.append(
        Paragraph(
            "Financial Dashboard",
            heading
        )
    )

    story.append(Spacer(1,15))

    savings_rate = 0
    expense_rate = 0

    if data["income"] > 0:
        savings_rate = round(
            (data["savings"] / data["income"]) * 100,
            1
        )

        expense_rate = round(
            (data["expense"] / data["income"]) * 100,
            1
        )

    dashboard = [

        ["Financial Indicator","Result"],

        ["Savings Rate",
         f"{savings_rate}%"],

        ["Expense Ratio",
         f"{expense_rate}%"],

        ["Monthly Cash Flow",
         f"₹ {data['savings']:,.0f}"],

        ["Risk Profile",
         data["risk"]],

        ["Financial Health Score",
         f"{data['score']} / 100"]

    ]

    dash_table = Table(
        dashboard,
        colWidths=[240,180]
    )

    dash_table.setStyle(table_style)

    story.append(dash_table)

    story.append(Spacer(1,30))

    ###################################################
    # FINANCIAL HEALTH INTERPRETATION
    ###################################################

    story.append(
        Paragraph(
            "Financial Health Interpretation",
            heading
        )
    )

    story.append(Spacer(1,10))

    if data["score"] >= 80:

        interpretation = """
        Your financial position appears strong.
        You maintain healthy savings and have good
        potential for long-term wealth creation.
        Continue investing consistently and review
        your portfolio periodically.
        """

    elif data["score"] >= 60:

        interpretation = """
        Your finances are on the right track.
        Increasing your savings rate and maintaining
        disciplined investing can significantly improve
        your long-term financial stability.
        """

    else:

        interpretation = """
        Your financial profile requires attention.
        Focus on reducing unnecessary expenses,
        increasing savings and building an emergency
        fund before taking higher investment risks.
        """

    story.append(
        Paragraph(
            interpretation,
            normal
        )
    )

    story.append(Spacer(1,25))

    ###################################################
    # RECOMMENDED INVESTMENT ALLOCATION
    ###################################################

    story.append(
        Paragraph(
            "Recommended Monthly Investment Allocation",
            heading
        )
    )

    story.append(Spacer(1,10))

    allocation = [

        ["Asset","Suggested Amount"],

        ["Mutual Fund SIP",
         f"₹ {data['sip']:,.0f}"],

        ["Large Cap Funds",
         f"₹ {data['large_cap']:,.0f}"],

        ["Mid Cap Funds",
         f"₹ {data['mid_cap']:,.0f}"],

        ["Small Cap Funds",
         f"₹ {data['small_cap']:,.0f}"],

        ["Emergency Fund",
         f"₹ {data['emergency_fund']:,.0f}"]

    ]

    allocation_table = Table(
        allocation,
        colWidths=[240,180]
    )

    allocation_table.setStyle(table_style)

    story.append(allocation_table)

    story.append(Spacer(1,30))

    ###################################################
    # KEY RECOMMENDATIONS
    ###################################################

    story.append(
        Paragraph(
            "Key Recommendations",
            heading
        )
    )

    story.append(Spacer(1,10))

    for advice in data["advice"]:

        story.append(
            Paragraph(
                f"• {advice}",
                normal
            )
        )

    story.append(PageBreak())
        ###################################################
    # FINANCIAL STRENGTHS
    ###################################################

    story.append(
        Paragraph(
            "Financial Strengths",
            heading
        )
    )

    story.append(Spacer(1,12))

    strengths = []

    if data["score"] >= 80:
        strengths.append("Excellent financial discipline demonstrated through a strong financial health score.")

    if data["savings"] > data["expense"]:
        strengths.append("Your monthly savings exceed your monthly expenses, creating a healthy cash surplus.")

    if data["risk"].lower() == "low":
        strengths.append("Conservative investment behaviour helps preserve capital.")

    elif data["risk"].lower() == "medium":
        strengths.append("Balanced investment approach suitable for long-term wealth creation.")

    else:
        strengths.append("Growth-oriented investment mindset provides higher long-term return potential.")

    if data["sip"] > 0:
        strengths.append("Regular investing has been recommended to build wealth consistently.")

    for item in strengths:
        story.append(Paragraph(f"✓ {item}", normal))

    story.append(Spacer(1,25))

    ###################################################
    # AREAS OF IMPROVEMENT
    ###################################################

    story.append(
        Paragraph(
            "Areas for Improvement",
            heading
        )
    )

    story.append(Spacer(1,12))

    improvements = []

    if savings_rate < 20:
        improvements.append("Increase your monthly savings rate to at least 20% of your income.")

    if expense_rate > 70:
        improvements.append("Review discretionary spending to improve monthly cash flow.")

    if data["score"] < 70:
        improvements.append("Focus on strengthening your overall financial health before taking additional investment risk.")

    improvements.append("Review your investment portfolio every six months.")

    improvements.append("Increase investments whenever your salary increases.")

    for item in improvements:
        story.append(Paragraph(f"• {item}", normal))

    story.append(PageBreak())

    ###################################################
    # AI FINANCIAL PERSONALITY
    ###################################################

    story.append(
        Paragraph(
            "AI Financial Personality",
            heading
        )
    )

    story.append(Spacer(1,12))

    if data["risk"].lower() == "low":

        personality = """
        Based on your financial profile, you appear to be a Conservative Investor.

        You prefer stability over aggressive returns and value financial security.
        Your strategy is suitable for preserving wealth while achieving steady growth.
        """

    elif data["risk"].lower() == "medium":

        personality = """
        Based on your financial profile, you appear to be a Balanced Investor.

        You maintain a healthy balance between risk and reward.
        This approach is considered appropriate for long-term wealth creation.
        """

    else:

        personality = """
        Based on your financial profile, you appear to be a Growth Investor.

        You are comfortable taking higher investment risks in pursuit of superior long-term returns.
        Portfolio diversification remains important.
        """

    story.append(
        Paragraph(
            personality,
            normal
        )
    )

    story.append(Spacer(1,25))

    ###################################################
    # SWOT ANALYSIS
    ###################################################

    story.append(
        Paragraph(
            "AI SWOT Analysis",
            heading
        )
    )

    story.append(Spacer(1,10))

    swot = [

        ["Category","Observation"],

        ["Strength",
         "Healthy savings habit and regular investment potential."],

        ["Weakness",
         "Income growth and expense optimisation can further improve wealth creation."],

        ["Opportunity",
         "Long-term investing can significantly increase future net worth through compounding."],

        ["Threat",
         "Inflation, lifestyle inflation and inadequate emergency reserves may impact future financial stability."]

    ]

    swot_table = Table(
        swot,
        colWidths=[150,270]
    )

    swot_table.setStyle(table_style)

    story.append(swot_table)

    story.append(PageBreak())
        ###################################################
    # WEALTH BUILDING PLAN
    ###################################################

    story.append(
        Paragraph(
            "Wealth Building Plan",
            heading
        )
    )

    story.append(Spacer(1,12))


    wealth_plan = [

        ["Timeline","Financial Focus"],

        ["Next 1 Year",
         "Build strong saving habits, maintain emergency fund and continue disciplined investing."],

        ["Next 5 Years",
         "Increase investment contributions and allow compounding to accelerate wealth creation."],

        ["Next 10 Years",
         "Focus on portfolio growth, diversification and achieving major financial milestones."],

        ["Next 20 Years",
         "Aim towards financial independence through consistent investing and wealth accumulation."]

    ]


    wealth_table = Table(
        wealth_plan,
        colWidths=[130,290]
    )

    wealth_table.setStyle(table_style)

    story.append(wealth_table)


    story.append(Spacer(1,30))


    ###################################################
    # FINANCIAL MILESTONES
    ###################################################

    story.append(
        Paragraph(
            "Your Financial Milestones",
            heading
        )
    )

    story.append(Spacer(1,12))


    milestones = [

        ["Milestone","Status"],

        ["Emergency Fund",
         "Build and maintain 6 months of expenses"],

        ["₹10 Lakh Portfolio",
         "First major investment milestone"],

        ["₹50 Lakh Portfolio",
         "Strong financial foundation"],

        ["₹1 Crore Portfolio",
         "Long-term wealth creation goal"]

    ]


    milestone_table = Table(
        milestones,
        colWidths=[180,240]
    )

    milestone_table.setStyle(table_style)

    story.append(milestone_table)


    story.append(PageBreak())


    ###################################################
    # FINANCIAL RATIOS
    ###################################################

    story.append(
        Paragraph(
            "Financial Ratio Analysis",
            heading
        )
    )

    story.append(Spacer(1,12))


    investment_ratio = 0

    if data["income"] > 0:

        investment_ratio = round(
            (data["sip"] / data["income"]) * 100,
            1
        )


    ratios = [

        ["Financial Metric","Percentage"],

        ["Savings Ratio",
         f"{savings_rate}%"],

        ["Expense Ratio",
         f"{expense_rate}%"],

        ["Investment Ratio",
         f"{investment_ratio}%"]

    ]


    ratio_table = Table(
        ratios,
        colWidths=[240,180]
    )

    ratio_table.setStyle(table_style)


    story.append(ratio_table)


    story.append(Spacer(1,30))


    ###################################################
    # EMERGENCY FUND ANALYSIS
    ###################################################

    story.append(
        Paragraph(
            "Emergency Fund Assessment",
            heading
        )
    )


    story.append(Spacer(1,12))


    emergency_text = """

    An emergency fund acts as your financial safety net.
    Ideally, maintain three to six months of essential expenses
    in liquid and easily accessible investments.

    """

    story.append(
        Paragraph(
            emergency_text,
            normal
        )
    )


    if data["emergency_fund"] > (data["expense"] * 6):

        emergency_status = "Excellent emergency preparedness."

    elif data["emergency_fund"] > (data["expense"] * 3):

        emergency_status = "Good emergency coverage. Continue strengthening reserves."

    else:

        emergency_status = "Emergency fund requires improvement."


    story.append(
        Paragraph(
            f"<b>Status:</b> {emergency_status}",
            normal
        )
    )


    story.append(Spacer(1,30))


    ###################################################
    # SIP GROWTH PROJECTION
    ###################################################

    story.append(
        Paragraph(
            "Long Term SIP Growth Projection",
            heading
        )
    )

    story.append(Spacer(1,12))


    sip_projection = [

        ["Period","Estimated Value"],

        ["5 Years",
         f"₹ {(data['sip']*12*5*1.5):,.0f}"],

        ["10 Years",
         f"₹ {(data['sip']*12*10*2.4):,.0f}"],

        ["20 Years",
         f"₹ {(data['sip']*12*20*4.5):,.0f}"]

    ]


    sip_table = Table(
        sip_projection,
        colWidths=[180,240]
    )

    sip_table.setStyle(table_style)


    story.append(sip_table)


    story.append(PageBreak())
        ###################################################
    # AI WEALTH ADVISOR
    ###################################################

    story.append(
        Paragraph(
            "SmartPlan AI Wealth Advisor",
            heading
        )
    )

    story.append(Spacer(1,12))


    if data.get("ai_advice"):

        ai_text = data["ai_advice"]

    else:

        if data["score"] >= 80:

            ai_text = """
            Your financial foundation is strong.
            Continue disciplined investing, increase SIP
            contributions gradually and review your portfolio
            periodically.

            Focus on maintaining consistency because long-term
            wealth is created through disciplined behaviour.
            """

        elif data["score"] >= 60:

            ai_text = """
            Your financial journey is progressing well.

            Consider improving your savings rate, building a stronger
            emergency fund and increasing investments whenever possible.

            Small improvements made consistently can create significant
            wealth over time.

            """

        else:

            ai_text = """
            Your financial health requires improvement.

            Start by controlling unnecessary expenses, creating an
            emergency fund and developing a disciplined investment habit.

            Financial success begins with strong fundamentals.

            """


    story.append(
        Paragraph(
            ai_text,
            normal
        )
    )


    story.append(Spacer(1,30))


    ###################################################
    # FINANCIAL HABITS SCORECARD
    ###################################################

    story.append(
        Paragraph(
            "Financial Behaviour Scorecard",
            heading
        )
    )

    story.append(Spacer(1,12))


    savings_score = 0
    investment_score = 0


    if data["income"] > 0:

        savings_percentage = (
            data["savings"] /
            data["income"]
        ) * 100


        investment_percentage = (
            data["sip"] /
            data["income"]
        ) * 100


        if savings_percentage >= 20:
            savings_score = 9

        elif savings_percentage >= 10:
            savings_score = 7

        else:
            savings_score = 5



        if investment_percentage >= 20:
            investment_score = 9

        elif investment_percentage >= 10:
            investment_score = 7

        else:
            investment_score = 5



    scorecard = [

        ["Category","Score"],

        ["Budget Management",
         "8 / 10"],

        ["Savings Discipline",
         f"{savings_score} / 10"],

        ["Investment Habit",
         f"{investment_score} / 10"],

        ["Risk Management",
         "7 / 10"],

        ["Retirement Planning",
         "8 / 10"]

    ]


    score_table = Table(
        scorecard,
        colWidths=[240,180]
    )


    score_table.setStyle(table_style)


    story.append(score_table)


    story.append(PageBreak())



    ###################################################
    # TAX PLANNING INSIGHT
    ###################################################

    story.append(
        Paragraph(
            "Tax Planning Insights",
            heading
        )
    )


    story.append(Spacer(1,12))


    tax_text = """

    Efficient tax planning helps increase your overall wealth creation
    potential.

    Consider evaluating tax-saving investments, retirement products
    and deductions available under applicable tax regulations.

    Always choose investments based on your financial goals rather
    than only tax benefits.

    """


    story.append(
        Paragraph(
            tax_text,
            normal
        )
    )


    story.append(Spacer(1,25))


    ###################################################
    # INVESTMENT DISCIPLINE MESSAGE
    ###################################################

    story.append(
        Paragraph(
            "Investment Discipline",
            heading
        )
    )


    story.append(Spacer(1,12))


    discipline = """

    Successful investing is not about predicting markets.

    It is about staying invested, maintaining discipline,
    diversifying appropriately and allowing the power of
    compounding to work over time.

    """

    story.append(
        Paragraph(
            discipline,
            normal
        )
    )


    story.append(PageBreak())



    ###################################################
    # IMPORTANT DISCLAIMER
    ###################################################

    story.append(
        Paragraph(
            "Important Disclaimer",
            heading
        )
    )


    story.append(Spacer(1,12))


    disclaimer = """

    SmartPlan Finance provides financial education and
    personalized insights based on information provided by the user.

    This report does not constitute investment advice,
    financial planning advice or a recommendation to buy or sell
    any financial product.

    Investment decisions involve market risks.
    Users should evaluate their personal financial situation and
    consult qualified professionals before making investment decisions.

    """

    story.append(
        Paragraph(
            disclaimer,
            normal
        )
    )


    story.append(Spacer(1,40))


    story.append(
        Paragraph(
            "<b>Generated by SmartPlan Finance AI</b><br/>"
            "Plan Smart. Invest Smarter.<br/><br/>"
            "www.smartplanfinance.com",
            styles["Italic"]
        )
    )


    ###################################################
    # BUILD PDF
    ###################################################

    doc.build(story)