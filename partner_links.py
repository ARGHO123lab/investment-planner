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

    # Internal SmartPlanFinance Loan Assistance
    "loan_assistance": {
        "name": "Loan Assistance",
        "url": "/loan-assistance",
        "cta": "Need a Loan? Connect with our Banking Partners",
        "tagline": "Explore Home, Personal and Vehicle Loan options through our banking partners.",
        "color": "#149721",
    },
}


# Which partner(s) appear on each calculator/page
PAGE_PARTNER_MAP = {

    "sip_calculator": [
        "groww",
        "zerodha"
    ],

    "financial_future": [
        "upstox",
        "zerodha"
    ],

    "retirement_calculator": [
        "indmoney"
    ],

    "tax_calculator": [
        "axis_salary",
        "zerodha"
    ],

    "emi_calculator": [
        "axis_salary",
        "loan_assistance"
    ],

    "fd_calculator": [
        "axis_savings"
    ],

    "dashboard": [
        "cred",
        "groww"
    ],
}


# Auto-select partner CTA for blog articles
KEYWORD_PARTNER_MAP = {

    "sip": "groww",

    "mutual fund": "groww",

    "investment": "zerodha",

    "stock": "zerodha",

    "trading": "upstox",

    "tax": "axis_salary",

    "salary": "axis_salary",

    "fd": "axis_savings",

    "fixed deposit": "axis_savings",

    "emergency fund": "axis_savings",

    "retirement": "indmoney",

    "wealth": "indmoney",

    "budget": "cred",

    # Loan-related articles
    "loan": "loan_assistance",

    "home loan": "loan_assistance",

    "personal loan": "loan_assistance",

    "car loan": "loan_assistance",

    "vehicle loan": "loan_assistance",

    "emi": "loan_assistance",

}