from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.units import inch

def generate_financial_report(output_path, user, data):
    doc = SimpleDocTemplate(
        output_path,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    story = []

    # Reusable table style for the new sections
    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#B8860B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ])

    # ----------------------------
    # Title
    # ----------------------------
    title = styles["Title"]
    title.alignment = TA_CENTER
    title.textColor = colors.HexColor("#B8860B")
    subtitle = styles["Heading2"]
    subtitle.alignment = TA_CENTER

    story.append(Paragraph("SMARTPLAN FINANCE", title))
    story.append(Paragraph("Personalized Financial Report", subtitle))
    story.append(Paragraph("Plan Smart. Invest Smarter.", styles["Italic"]))
    story.append(Spacer(1, 0.35 * inch))

    # ----------------------------
    # Client Details
    # ----------------------------
    story.append(Paragraph("<b>Client Details</b>", styles["Heading2"]))
    story.append(Paragraph(f"<b>Name:</b> {user['name']}", styles["Normal"]))
    story.append(Paragraph(f"<b>Country:</b> {user['country']}", styles["Normal"]))
    story.append(Spacer(1, 0.30 * inch))

    # ----------------------------
    # Financial Summary
    # ----------------------------
    story.append(Paragraph("<b>Financial Summary</b>", styles["Heading2"]))
    table_data = [
        ["Particular", "Value"],
        ["Monthly Income", f"₹ {data['income']:,.0f}"],
        ["Monthly Expense", f"₹ {data['expense']:,.0f}"],
        ["Monthly Savings", f"₹ {data['savings']:,.0f}"],
        ["Financial Score", str(data["score"])]
    ]
    table = Table(table_data, colWidths=[250, 180])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4D03F")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.35 * inch))

    # ----------------------------
    # Investment Recommendation
    # ----------------------------
    story.append(Paragraph("<b>Investment Recommendation</b>", styles["Heading2"]))
    recommendation = [
        ["Asset Class", "Suggested Monthly Investment"],
        ["SIP Investment", f"₹ {data['sip']:,.0f}"],
        ["Large Cap", f"₹ {data['large_cap']:,.0f}"],
        ["Mid Cap", f"₹ {data['mid_cap']:,.0f}"],
        ["Small Cap", f"₹ {data['small_cap']:,.0f}"],
        ["Emergency Fund", f"₹ {data['emergency_fund']:,.0f}"]
    ]
    invest_table = Table(recommendation, colWidths=[250, 180])
    invest_table.setStyle(table_style)
    story.append(invest_table)
    story.append(Spacer(1, 0.35 * inch))

    # ----------------------------
    # NEW SECTIONS
    # ----------------------------

    # SIP PROJECTION
    if data.get("sip_calc_fv", 0) > 0:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>SIP Projection</b>", styles["Heading2"]))
        sip_table = Table([["Monthly Investment", f"₹ {data['sip_calc_monthly']:,.0f}"], ["Duration", f"{data['sip_calc_years']} Years"], ["Future Value", f"₹ {data['sip_calc_fv']:,.0f}"]], colWidths=[250, 180])
        sip_table.setStyle(table_style)
        story.append(sip_table)

    # FINANCIAL GOAL PLANNER
    if data.get("future_target_amount", 0) > 0:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Financial Goal Planner</b>", styles["Heading2"]))
        goal_table = Table([["Goal Amount", f"₹ {data['future_target_amount']:,.0f}"], ["Time Horizon", f"{data['future_target_years']} Years"], ["Monthly Investment Required", f"₹ {data['future_req_monthly']:,.0f}"]], colWidths=[250, 180])
        goal_table.setStyle(table_style)
        story.append(goal_table)

    # EMI ANALYSIS
    if data.get("emi_monthly", 0) > 0:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>EMI Analysis</b>", styles["Heading2"]))
        emi_table = Table([["Loan Amount", f"₹ {data['emi_loan_amount']:,.0f}"], ["Interest Rate", f"{data['emi_rate']} %"], ["Loan Tenure", f"{data['emi_years']} Years"], ["Monthly EMI", f"₹ {data['emi_monthly']:,.0f}"], ["Total Interest", f"₹ {data['emi_interest']:,.0f}"], ["Total Payment", f"₹ {data['emi_total']:,.0f}"]], colWidths=[250, 180])
        emi_table.setStyle(table_style)
        story.append(emi_table)

    # RETIREMENT PLANNER
    if data.get("retirement_corpus", 0) > 0:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Retirement Planner</b>", styles["Heading2"]))
        ret_table = Table([["Retirement Age", data["retirement_age"]], ["Retirement Corpus", f"₹ {data['retirement_corpus']:,.0f}"], ["Monthly SIP Required", f"₹ {data['retirement_monthly']:,.0f}"]], colWidths=[250, 180])
        ret_table.setStyle(table_style)
        story.append(ret_table)

    # FIXED DEPOSIT
    if data.get("fd_maturity", 0) > 0:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Fixed Deposit Analysis</b>", styles["Heading2"]))
        fd_table = Table([["Deposit Amount", f"₹ {data['fd_principal']:,.0f}"], ["Interest Rate", f"{data['fd_rate']} %"], ["Duration", f"{data['fd_years']} Years"], ["Interest Earned", f"₹ {data['fd_interest']:,.0f}"], ["Maturity Amount", f"₹ {data['fd_maturity']:,.0f}"]], colWidths=[250, 180])
        fd_table.setStyle(table_style)
        story.append(fd_table)

    # TAX REGIME
    if data.get("tax_old", 0) > 0 or data.get("tax_new", 0) > 0:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Tax Regime Comparison</b>", styles["Heading2"]))
        tax_table = Table([["Annual Income", f"₹ {data['tax_income']:,.0f}"], ["Old Regime Tax", f"₹ {data['tax_old']:,.0f}"], ["New Regime Tax", f"₹ {data['tax_new']:,.0f}"], ["Tax Savings", f"₹ {data['tax_savings']:,.0f}"], ["Recommended Regime", data["tax_better"]]], colWidths=[250, 180])
        tax_table.setStyle(table_style)
        story.append(tax_table)

    # ----------------------------
    # Recommendations & Footer
    # ----------------------------
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("<b>SmartPlan Finance Recommendations</b>", styles["Heading2"]))
    for advice in data["advice"]:
        story.append(Paragraph(f"• {advice}", styles["Normal"]))

    story.append(Spacer(1, 0.40 * inch))
    footer = styles["Italic"]
    footer.alignment = TA_CENTER
    story.append(Paragraph("SmartPlan Finance", footer))
    story.append(Paragraph("www.smartplanfinance.com", footer))
    story.append(Paragraph("This report is computer generated and intended for educational purposes only.", footer))

    doc.build(story)