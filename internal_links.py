import re

CALCULATOR_LINKS = {
    "sip": (
        "SIP Calculator",
        "/sip-calculator"
    ),
    "mutual fund": (
        "SIP Calculator",
        "/sip-calculator"
    ),
    "financial goal": (
        "Financial Goal Planner",
        "/financial-future"
    ),
    "goal planning": (
        "Financial Goal Planner",
        "/financial-future"
    ),
    "emi": (
        "EMI Calculator",
        "/emi_calculator"
    ),
    "loan": (
        "EMI Calculator",
        "/emi_calculator"
    ),
    "retirement": (
        "Retirement Calculator",
        "/retirement_calculator"
    ),
    "tax": (
        "Income Tax Calculator",
        "/tax_calculator"
    ),
    "income tax": (
        "Income Tax Calculator",
        "/tax_calculator"
    ),
    "fixed deposit": (
        "FD Calculator",
        "/fd_calculator"
    ),
    "fd": (
        "FD Calculator",
        "/fd_calculator"
    )
}


def insert_internal_links(html):

    modified = html

    used = set()

    for keyword, (title, url) in CALCULATOR_LINKS.items():

        if keyword in used:
            continue

        pattern = re.compile(
            rf"\b{re.escape(keyword)}\b",
            re.IGNORECASE
        )

        match = pattern.search(modified)

        if match:

            replacement = (
                f'<a href="{url}">{match.group(0)}</a>'
            )

            modified = pattern.sub(
                replacement,
                modified,
                count=1
            )

            used.add(keyword)

    return modified