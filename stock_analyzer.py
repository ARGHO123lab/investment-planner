import math
import yfinance as yf
from rapidfuzz import process
from stock_symbols import COMPANY_SYMBOLS
import ta


def safe_round(value, digits=2):
    try:
        if value is None or math.isnan(float(value)):
            return None
        return round(float(value), digits)
    except:
        return None


def format_number(num):

    if num is None:
        return "N/A"

    try:
        num = float(num)
    except:
        return num

    if math.isnan(num):
        return "N/A"

    if num >= 1_000_000_000_000:
        return f"₹ {num/1_000_000_000_000:.2f} Trillion"

    if num >= 10_000_000:
        return f"₹ {num/10_000_000:.2f} Crore"

    return f"{num:,.0f}"


def get_best_symbol(user_input):

    user_input = user_input.upper().strip()
    user_input = " ".join(user_input.split())

    if user_input in COMPANY_SYMBOLS:
        ticker = COMPANY_SYMBOLS[user_input]

    else:

        match = process.extractOne(
            user_input,
            COMPANY_SYMBOLS.keys(),
            score_cutoff=75
        )

        if match:
            print(
                f"Matched '{user_input}' -> '{match[0]}'"
            )
            ticker = COMPANY_SYMBOLS[match[0]]

        else:
            ticker = user_input


    if not ticker.endswith(".NS"):
        ticker += ".NS"


    return ticker



def get_stock_data(symbol):

    try:

        symbol = get_best_symbol(symbol)

        print("="*60)
        print("Searching Yahoo:", symbol)


        stock = yf.Ticker(symbol)


        history = stock.history(
            period="10y",
            auto_adjust=True
        )


        if history.empty:
            print("No historical data")
            return None



        close = history["Close"].dropna()



        if len(close) == 0:
            return None



        # -------------------------
        # Technical Analysis
        # -------------------------

        history["SMA20"] = ta.trend.sma_indicator(
            close,
            window=20
        )

        history["SMA50"] = ta.trend.sma_indicator(
            close,
            window=50
        )


        history["SMA200"] = ta.trend.sma_indicator(
            close,
            window=200
        )


        history["RSI"] = ta.momentum.rsi(
            close,
            window=14
        )


        macd = ta.trend.MACD(close)

        history["MACD"] = macd.macd()

        history["MACD_SIGNAL"] = macd.macd_signal()



        history["AVG_VOLUME"] = (
            history["Volume"]
            .rolling(20)
            .mean()
        )



        latest = history.iloc[-1]



        try:
            info = stock.info
        except:
            info = {}



        current_price = safe_round(
            close.iloc[-1]
        )


        one_year_return = None
        five_year_return = None



        if len(close) >= 252:

            old = close.iloc[-252]

            one_year_return = safe_round(
                ((current_price-old)/old)*100
            )


        if len(close) >= 1260:

            old = close.iloc[-1260]

            five_year_return = safe_round(
                ((current_price-old)/old)*100
            )



        data = {


            "symbol": symbol,


            "company_name":
                info.get(
                    "longName",
                    symbol.replace(".NS","")
                ),


            "sector":
                info.get(
                    "sector",
                    "N/A"
                ),


            "industry":
                info.get(
                    "industry",
                    "N/A"
                ),


            "current_price": current_price,


            "market_cap":
                format_number(
                    info.get("marketCap")
                ),


            "pe_ratio":
                safe_round(
                    info.get("trailingPE")
                ),


            "forward_pe":
                safe_round(
                    info.get("forwardPE")
                ),


            "pb_ratio":
                safe_round(
                    info.get("priceToBook")
                ),


            "roe":
                safe_round(
                    info.get("returnOnEquity")
                ),


            "debt_to_equity":
                safe_round(
                    info.get("debtToEquity")
                ),


            "beta":
                safe_round(
                    info.get("beta")
                ),


            "dividend_yield":
                safe_round(
                    info.get("dividendYield")
                ),


            "revenue":
                format_number(
                    info.get("totalRevenue")
                ),


            "net_income":
                format_number(
                    info.get("netIncomeToCommon")
                ),


            "cash":
                format_number(
                    info.get("totalCash")
                ),


            "fifty_two_week_high":
                info.get(
                    "fiftyTwoWeekHigh"
                ),


            "fifty_two_week_low":
                info.get(
                    "fiftyTwoWeekLow"
                ),


            "one_year_return":
                one_year_return,


            "five_year_return":
                five_year_return,



            # Technical

            "moving_average_20":
                safe_round(
                    latest["SMA20"]
                ),


            "moving_average_50":
                safe_round(
                    latest["SMA50"]
                ),


            "moving_average_200":
                safe_round(
                    latest["SMA200"]
                ),


            "rsi":
                safe_round(
                    latest["RSI"]
                ),


            "macd":
                safe_round(
                    latest["MACD"]
                ),


            "macd_signal":
                safe_round(
                    latest["MACD_SIGNAL"]
                ),


            "average_volume":
                format_number(
                    latest["AVG_VOLUME"]
                )

        }



        print(
            "Success:",
            data["company_name"]
        )


        return data



    except Exception as e:

        print(
            "Stock Analyzer Error:",
            e
        )

        return None