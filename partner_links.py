# partner_links.py

PARTNER_LINKS = {
    "groww": {
        "name": "Groww",
        "url": "https://app.groww.in/v3cO/sbkp7vq2",
        "cta": "Start Your SIP with Groww",
        "tagline": "Zero-commission direct mutual funds & stocks",
        "color": "#00D09C",
    },
    "zerodha": {
        "name": "Zerodha",
        "url": "https://zerodha.com/open-account?c=QND477",
        "cta": "Open a Free Zerodha Demat Account",
        "tagline": "India's largest stock broker",
        "color": "#387ED1",
    },
    "upstox": {
        "name": "Upstox",
        "url": "https://upstox.onelink.me/0H1s/62CL8Z",
        "cta": "Trade Smarter with Upstox",
        "tagline": "Fast, low-cost trading platform",
        "color": "#5C2D91",
    },
    "indmoney": {
        "name": "INDmoney",
        "url": "https://indmoney.onelink.me/RmHC/2jk1z9vk",
        "cta": "Track & Grow Wealth with INDmoney",
        "tagline": "All-in-one wealth tracking & investing app",
        "color": "#00B899",
    },
    "cred": {
        "name": "CRED",
        "url": "https://app.cred.club/spQx/yfjmxcmg",
        "cta": "Manage Bills Smartly with CRED",
        "tagline": "Pay credit card bills, earn rewards",
        "color": "#1C1C1E",
    },
    "axis_savings": {
        "name": "Axis Bank Savings",
        "url": "https://axmobile.axis.bank.in/refernearn/services/refer/31ae272523cf41a5ad88a12bd0901541",
        "cta": "Open a Free Axis Savings Account",
        "tagline": "Digital savings account in minutes",
        "color": "#97144D",
    },
    "axis_salary": {
        "name": "Axis Bank Salary Account",
        "url": "https://axmobile.axis.bank.in/refernearn/services/refer/e79714052d91494eaed9c1e329202e48",
        "cta": "Switch to an Axis Salary Account",
        "tagline": "Zero-balance account with salary perks",
        "color": "#97144D",
    },
}

# Which partner(s) show up on which tool/page — this mapping is the whole
# "creative" layer. Keep the reasoning here, not scattered in templates.
PAGE_PARTNER_MAP = {
    "sip_calculator":       ["groww", "zerodha"],
    "financial_future":     ["upstox", "zerodha"],
    "retirement_calculator":["indmoney"],
    "tax_calculator":       ["axis_salary", "zerodha"],
    "emi_calculator":       ["axis_salary"],
    "fd_calculator":        ["axis_savings"],
    "dashboard":            ["cred", "groww"],
}

# Blog articles: reuse the keyword list you ALREADY compute in view_article()
# to auto-pick a relevant partner instead of a generic banner.
KEYWORD_PARTNER_MAP = {
    "sip": "groww",
    "investment": "zerodha",
    "mutual fund": "groww",
    "tax": "axis_salary",
    "retirement": "indmoney",
    "fd": "axis_savings",
    "emergency fund": "axis_savings",
    "wealth": "indmoney",
    "salary": "axis_salary",
    "budget": "cred",
}