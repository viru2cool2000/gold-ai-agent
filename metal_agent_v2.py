from dotenv import load_dotenv
import os
import requests
import time
from datetime import datetime
from twilio.rest import Client

# -------------------------------
# LOAD ENV
# -------------------------------
load_dotenv()

# -------------------------------
# CONFIG
# -------------------------------
METALS = {
    "Gold": "XAU",
    "Silver": "XAG",
    "Platinum": "XPT",
    "Palladium": "XPD"
}

FX_API = "https://open.er-api.com/v6/latest/USD"
METAL_API = "https://api.gold-api.com/price"
REFRESH_SECONDS = 300

# WHATSAPP (TWILIO)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_WHATSAPP = os.getenv("FROM_WHATSAPP")
TO_WHATSAPP = os.getenv("TO_WHATSAPP")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

TROY_OUNCE_TO_GRAM = 31.1035
INDIA_LANDED_FACTOR = 1.065

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ALERT CONFIG
THRESHOLD_METALS = ["Gold", "Silver"]
PRICE_CHANGE_THRESHOLD = 50
WHATSAPP_ENABLED = True

# DAILY REPORT
DAILY_REPORT_HOUR = 9
DAILY_REPORT_MIN = 0

# SNAPSHOT (LOCAL AGENT)
SNAPSHOT_INTERVAL_SECONDS = 3 * 60 * 60
LAST_SNAPSHOT_TIME = None

# MEMORY
LAST_PRICES = {}
LAST_DAILY_REPORT_DATE = None


# -------------------------------
# FX RATE
# -------------------------------
def get_usd_to_inr():
    r = requests.get(FX_API, timeout=10)
    r.raise_for_status()
    return r.json()["rates"]["INR"]


# -------------------------------
# METAL PRICE WITH RETRY
# -------------------------------
def get_metal_price_inr(symbol, fx_rate):
    url = f"{METAL_API}/{symbol}"

    for attempt in range(3):
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.json()["price"] * fx_rate
        except Exception as e:
            print(f"Retry {attempt+1} for {symbol} failed:", e)
            time.sleep(2)

    raise Exception(f"Failed to fetch {symbol} price after retries")


# -------------------------------
# CALCULATIONS
# -------------------------------
def calculate_prices(price_oz_inr):
    price_g = price_oz_inr / TROY_OUNCE_TO_GRAM
    india_price = price_g * INDIA_LANDED_FACTOR
    return round(price_g, 2), round(india_price, 2)


def calculate_bias(old_price, new_price):
    if old_price is None:
        return "NEUTRAL"
    change = new_price - old_price
    if change > 0:
        return "BULLISH"
    elif change < 0:
        return "BEARISH"
    return "NEUTRAL"


# -------------------------------
# WHATSAPP
# -------------------------------
def send_whatsapp(message):
    if not WHATSAPP_ENABLED:
        return

    try:
        twilio_client.messages.create(
            body=message,
            from_=FROM_WHATSAPP,
            to=TO_WHATSAPP
        )
        print("📲 WhatsApp sent successfully")
    except Exception as e:
        print("❌ WhatsApp send failed:", e)


# -------------------------------
# NEWS
# -------------------------------
def get_market_news():
    try:
        url_metal = (
            "https://newsapi.org/v2/everything?"
            "q=gold OR silver commodity&"
            "language=en&sortBy=publishedAt&pageSize=1&"
            f"apiKey={NEWS_API_KEY}"
        )

        r = requests.get(url_metal, timeout=10)
        data = r.json()
        articles = data.get("articles", [])

        if articles:
            return "📰 " + articles[0]["title"]

    except Exception as e:
        print("News fetch error:", e)

    return "📰 No major gold/silver news."


# -------------------------------
# FETCH ALL PRICES
# -------------------------------
def fetch_all_prices():
    fx_rate = get_usd_to_inr()
    prices = {}

    for metal, symbol in METALS.items():
        price_oz = get_metal_price_inr(symbol, fx_rate)
        price_g, india_price = calculate_prices(price_oz)

        prices[metal] = {
            "oz": round(price_oz, 2),
            "gram": price_g,
            "india": india_price
        }

    return prices, fx_rate


# -------------------------------
# ALERTS
# -------------------------------
def process_alerts(prices):
    global LAST_PRICES

    for metal in THRESHOLD_METALS:
        data = prices.get(metal)
        if not data:
            continue

        current = data["india"]
        previous = LAST_PRICES.get(metal)
        bias = calculate_bias(previous, current)

        if previous is not None:
            diff = current - previous

            if abs(diff) >= PRICE_CHANGE_THRESHOLD:
                news = get_market_news()
                other = "Silver" if metal == "Gold" else "Gold"
                other_price = prices.get(other, {}).get("india", "N/A")

                msg = (
                    f"🟡 {metal} Alert\n"
                    f"Now: ₹{current} / g\n"
                    f"Change: ₹{round(diff, 2)}\n"
                    f"Bias: {bias}\n"
                    f"{other}: ₹{other_price} / g\n\n"
                    f"{news}"
                )
                send_whatsapp(msg)

        LAST_PRICES[metal] = current


# -------------------------------
# SNAPSHOT (LOCAL 3H)
# -------------------------------
def whatsapp_snapshot(prices):
    global LAST_SNAPSHOT_TIME
    now = time.time()

    if LAST_SNAPSHOT_TIME is None:
        LAST_SNAPSHOT_TIME = now
        return

    if now - LAST_SNAPSHOT_TIME >= SNAPSHOT_INTERVAL_SECONDS:
        whatsapp_snapshot_force(prices)
        LAST_SNAPSHOT_TIME = now


# -------------------------------
# SNAPSHOT (FORCED - GITHUB)
# -------------------------------
def whatsapp_snapshot_force(prices):
    msg = "🟡 Gold & Silver Rate Snapshot\n\n"

    gold = prices.get("Gold")
    if gold:
        msg += (
            "Gold\n"
            f"Spot(g): ₹{gold['gram']}\n"
            f"India: ₹{gold['india']}\n\n"
        )

    silver = prices.get("Silver")
    if silver:
        msg += f"Silver: ₹{silver['india']} / g\n\n"

    msg += get_market_news()
    send_whatsapp(msg)


# -------------------------------
# RUNNER (LOCAL)
# -------------------------------
def run_agent():
    while True:
        try:
            prices, fx = fetch_all_prices()
            process_alerts(prices)
            whatsapp_snapshot(prices)
            time.sleep(REFRESH_SECONDS)
        except Exception as e:
            print("❌ Error:", e)
            time.sleep(30)


# -------------------------------
# RUNNER (GITHUB)
# -------------------------------
def run_once():
    try:
        prices, fx = fetch_all_prices()
        process_alerts(prices)
        whatsapp_snapshot_force(prices)
    except Exception as e:
        send_whatsapp(f"❌ Agent error: {str(e)}")


# -------------------------------
# START
# -------------------------------
if __name__ == "__main__":
    import sys
    if "--once" in sys.argv:
        run_once()
    else:
        run_agent()
