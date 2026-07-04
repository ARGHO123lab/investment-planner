# ============================
# Global Country Configuration
# ============================

COUNTRIES = {

    "India": {
        "currency_symbol": "₹",
        "currency_code": "INR"
    },

    "United States": {
        "currency_symbol": "$",
        "currency_code": "USD"
    },

    "United Kingdom": {
        "currency_symbol": "£",
        "currency_code": "GBP"
    },

    "Canada": {
        "currency_symbol": "C$",
        "currency_code": "CAD"
    },

    "Australia": {
        "currency_symbol": "A$",
        "currency_code": "AUD"
    }

}


# ============================
# Risk Allocation Models
# ============================

RISK_MODELS = {

    "high": {

        "sip": 0.50,
        "large_cap": 0.20,
        "mid_cap": 0.15,
        "small_cap": 0.10,
        "emergency_fund": 0.05

    },

    "medium": {

        "sip": 0.40,
        "large_cap": 0.25,
        "mid_cap": 0.15,
        "small_cap": 0.05,
        "emergency_fund": 0.15

    },

    "low": {

        "sip": 0.25,
        "large_cap": 0.30,
        "mid_cap": 0.10,
        "small_cap": 0.05,
        "emergency_fund": 0.30

    }

}