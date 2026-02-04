from dotenv import load_dotenv
import os

load_dotenv()

import requests
import time
from datetime import datetime
from twilio.rest import Client


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


FROM_WHATSAPP = "whatsapp:+14155238886"   # Twilio sandbox / approved number
TO_WHATSAPP = "whatsapp:+919972700255"    # Your number

TROY_OUNCE_TO_GRAM = 31.1035
INDIA_LANDED_FACTOR = 1.065

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ALERT CONFIG
THRESHOLD_METALS = ["Gold", "Silver"]
PRICE_CHANGE_THRESHOLD = 50  # ₹ per gram (India est)
WHATSAPP_ENABLED = True

# DAILY REPORT
DAILY_REPORT_HOUR = 9
DAILY_REPORT_MIN = 0

# PERIODIC WHATSAPP SNAPSHOT (EVERY 3 HOURS)
SNAPSHOT_INTERVAL_SECONDS = 3 * 60 * 60  # 3 hours
LAST_SNAPSHOT_TIME = None


# MEMORY (runtime only)
LAST_PRICES = {}
LAST_DAILY_REPORT_DATE = None

# FX RATE
# -------------------------------
def get_usd_to_inr():
    r = requests.get(FX_API, timeout=10)
    r.raise_for_status()
    return r.json()["rates"]["INR"]


# -------------------------------
# METAL PRICE (OZ)
# -------------------------------
def get_metal_price_inr(symbol, fx_rate):
    r = requests.get(f"{METAL_API}/{symbol}", timeout=10)
    r.raise_for_status()
    return r.json()["price"] * fx_rate


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


def get_market_news():
    try:
        # 1️⃣ Priority: Gold & Silver news (global)
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

        # 2️⃣ Fallback: Indian + global economy news
        url_econ = (
            "https://newsapi.org/v2/top-headlines?"
            "country=in&category=business&pageSize=1&"
            f"apiKey={NEWS_API_KEY}"
        )

        r = requests.get(url_econ, timeout=10)
        data = r.json()
        articles = data.get("articles", [])

        if articles:
            return "📰 " + articles[0]["title"]

    except Exception as e:
        print("News fetch error:", e)

    return "📰 No major gold/silver or economy news at the moment."


# MAIN ENGINE
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

                # one-line reference for the other metal
                other_metal = "Silver" if metal == "Gold" else "Gold"
                other_price = prices.get(other_metal, {}).get("india", "N/A")

                msg = (
                    f"🟡 {metal} Alert\n"
                    f"Now: ₹{current} / g\n"
                    f"Change: ₹{round(diff, 2)}\n"
                    f"Bias: {bias}\n"
                    f"{other_metal}: ₹{other_price} / g\n\n"
                    f"{news}"
                )

                send_whatsapp(msg)

        # update memory
        LAST_PRICES[metal] = current
	
       
def daily_report(prices):
    global LAST_DAILY_REPORT_DATE

    now = datetime.now()
    today = now.date()

    if (
        now.hour == DAILY_REPORT_HOUR
        and now.minute == DAILY_REPORT_MIN
        and LAST_DAILY_REPORT_DATE != today
    ):
        report = "🟡 Daily Metal Report\n\n"

        for metal, data in prices.items():
            report += (
                f"{metal}\n"
                f"Spot(g): ₹{data['gram']}\n"
                f"India: ₹{data['india']}\n\n"
            )

        send_whatsapp(report)
        LAST_DAILY_REPORT_DATE = today

def whatsapp_snapshot(prices):
    global LAST_SNAPSHOT_TIME

    now = time.time()

    if LAST_SNAPSHOT_TIME is None:
        LAST_SNAPSHOT_TIME = now
        return

    if now - LAST_SNAPSHOT_TIME >= SNAPSHOT_INTERVAL_SECONDS:
        msg = "🟡 Gold & Silver Rate Snapshot\n\n"

        for metal in ["Gold", "Silver"]:
            data = prices.get(metal)
            if not data:
                continue

            msg += (
                f"{metal}\n"
                f"Spot(g): ₹{data['gram']}\n"
                f"India: ₹{data['india']}\n\n"
            )

        send_whatsapp(msg)
        LAST_SNAPSHOT_TIME = now

# RUNNER
send_whatsapp("✅ Gold AI Agent: WhatsApp integration successful!")
def run_agent():
    while True:
        try:
            prices, fx = fetch_all_prices()
            now = datetime.now().strftime("%d %b %Y | %I:%M %p")

            print("\n🟡 Metal Market Update")
            print(f"USD → INR: {round(fx, 4)}")
            print(f"Time: {now}\n")

            for metal, data in prices.items():
                print(f"{metal}")
                print(f"  Spot (oz): ₹{data['oz']}")
                print(f"  Spot (g):  ₹{data['gram']}")
                print(f"  India est: ₹{data['india']}\n")

            # 🔔 AUTOMATIONS (PASTE HERE)
            process_alerts(prices)
            daily_report(prices)
            whatsapp_snapshot(prices)

            time.sleep(REFRESH_SECONDS)

        except Exception as e:
            print("❌ Error:", e)
            time.sleep(30)




# -------------------------------
# START
# -------------------------------
if __name__ == "__main__":
    run_agent()
