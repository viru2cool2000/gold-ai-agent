import os
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

TROY_OUNCE_TO_GRAM = 31.1035
INDIA_LANDED_FACTOR = 1.065

# -------------------------------
# WHATSAPP (TWILIO)
# -------------------------------
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

FROM_WHATSAPP = "whatsapp:+14155238886"
TO_WHATSAPP = "whatsapp:+919972700255"

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# -------------------------------
# ALERT CONFIG
# -------------------------------
THRESHOLD_METALS = ["Gold", "Silver"]
PRICE_CHANGE_THRESHOLD = 50
LAST_PRICES = {}

# -------------------------------
# NEWS
# -------------------------------
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

def get_market_news():
    try:
        url = (
            "https://newsapi.org/v2/everything?"
            "q=gold OR silver commodity&"
            "language=en&sortBy=publishedAt&pageSize=1&"
            f"apiKey={NEWS_API_KEY}"
        )
        r = requests.get(url, timeout=10)
        data = r.json()
        articles = data.get("articles", [])
        if articles:
            return "📰 " + articles[0]["title"]
    except:
        pass

    return "📰 No major gold/silver news."

# -------------------------------
# WHATSAPP
# -------------------------------
def send_whatsapp(message):
    try:
        twilio_client.messages.create(
            body=message,
            from_=FROM_WHATSAPP,
            to=TO_WHATSAPP
        )
        print("📲 WhatsApp sent")
    except Exception as e:
        print("❌ WhatsApp error:", e)

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
            print(f"Retry {attempt+1} for {symbol}:", e)
            time.sleep(2)

    raise Exception(f"Failed to fetch {symbol}")

# -------------------------------
# CALCULATIONS
# -------------------------------
def calculate_prices(price_oz_inr):
    price_g = price_oz_inr / TROY_OUNCE_TO_GRAM
    india_price = price_g * INDIA_LANDED_FACTOR
    return round(price_g, 2), round(india_price, 2)

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
                    f"{other}: ₹{other_price} / g\n\n"
                    f"{news}"
                )
                send_whatsapp(msg)

        LAST_PRICES[metal] = current

# -------------------------------
# SNAPSHOT (GITHUB HOURLY)
# -------------------------------
def whatsapp_snapshot(prices):
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
# GITHUB RUN
# -------------------------------
def run_once():
    try:
        prices, fx = fetch_all_prices()
        process_alerts(prices)
        whatsapp_snapshot(prices)
    except Exception as e:
        send_whatsapp(f"❌ Agent error: {str(e)}")

# -------------------------------
# START
# -------------------------------
if __name__ == "__main__":
    run_once()
