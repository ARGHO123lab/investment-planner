import requests
import json


def generate_stock_analysis(stock, age, risk, years):

    prompt = f"""

You are a financial education assistant for SmartPlanFinance.

Analyze this stock for educational purposes only.

Company:
{stock['company_name']}

Sector:
{stock['sector']}

Current Price:
₹{stock['current_price']}

PE Ratio:
{stock['pe_ratio']}

Forward PE:
{stock['forward_pe']}

Price To Book:
{stock['pb_ratio']}

ROE:
{stock['roe']}

Debt Equity:
{stock['debt_to_equity']}

Market Cap:
{stock['market_cap']}

Revenue:
{stock['revenue']}

Net Income:
{stock['net_income']}

52 Week High:
{stock['fifty_two_week_high']}

52 Week Low:
{stock['fifty_two_week_low']}

1 Year Return:
{stock['one_year_return']}%

5 Year Return:
{stock['five_year_return']}%

Technical Indicators:

20 Day Moving Average:
{stock['moving_average_20']}

50 Day Moving Average:
{stock['moving_average_50']}

200 Day Moving Average:
{stock['moving_average_200']}

RSI:
{stock['rsi']}

MACD:
{stock['macd']}


Investor Profile:

Age:
{age}

Risk Appetite:
{risk}

Investment Horizon:
{years} years


Generate a professional HTML report.

Include:

1. AI Stock Health Score /100

2. Risk Level

3. Long term stability analysis

4. Explain:
PE Ratio
Moving Average
RSI
MACD
ROE
Debt Equity

5. Strengths

6. Weaknesses

7. Investor suitability based on age and risk profile

8. Long term outlook


Never say BUY or SELL.

Never guarantee returns.

Use:
"may consider"
"appears suitable"
"requires further evaluation"

End with:

SmartPlanFinance provides educational insights only.
This is not financial advice.
Investments are subject to market risks.

"""


    try:

        response = requests.post(

            "http://localhost:11434/api/generate",

            json={
                "model":"llama3.2:3b",
                "prompt":prompt,
                "stream":False
            }

        )


        result=response.json()

        return result["response"]


    except Exception as e:

        print("OLLAMA ERROR:",e)

        return """
        <div class='alert alert-danger'>
        AI service unavailable.
        </div>
        """