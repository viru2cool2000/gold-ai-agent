import requests
import os
from datetime import datetime
from twilio.rest import Client

# ==============================
# API KEYS
# ==============================
GOLD_API_KEY = os.getenv("GOLD_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# ==============================
# HARD-CODED WHATSAPP NUMBERS
# ==============================
TWILIO_FROM = "whatsapp:+14155238886"   # Twilio sandbox number
TWILIO_TO = "whatsapp:+919972700255"    # ← replace with your real number

# ==============================
# NEWS FILTER SETTINGS
# ==============================
ALLOWED_KEYWORDS = [
    "gold", "silver", "bullion", "precious",
    "usd", "dollar", "rupee", "inr",
    "inflation", "interest rate", "fed",
    "federal reserve", "rbi", "central bank",
    "economy", "recession", "bond",
    "treasury", "geopolitical", "oil"
]

BLOCKED_KEYWORDS = [
    "router", "wifi", "iphone", "android",
    "gaming", "crypto", "bitcoin", "ai",
    "chatgpt", "software", "app",
    "update", "hack", "cyber",
    "server", "laptop", "pc", "tech"
]

# ==============================
# PRICE FUNCTIONS
# ==============================
# ==============================
# PRICE FUNCTIONS (FREE API)
# ==============================
def get_gold_silver():
    gold_price = "N/A"
    silver_price = "N/A"
    usd_inr = None

    # Get USD/INR first
    try:
        fx = requests.get(
            "https://api.exchangerate.host/latest?base=USD&symbols=INR",
            timeout=10
        ).json()
        usd_inr = fx["rates"]["INR"]
    except:
        pass

    # Get gold price (USD/oz)
    try:
        res = requests.get("https://api.gold-api.com/price/XAU", timeout=10)
        data = res.json()
        gold_usd_per_oz = data["price"]

        if usd_inr:
            gold_price = round((gold_usd_per_oz * usd_inr) / 31.1035, 2)
    except:
        pass

    # Get silver price (USD/oz)
    try:
        res = requests.get("https://api.gold-api.com/price/XAG", timeout=10)
        data = res.json()
        silver_usd_per_oz = data["price"]

        if usd_inr:
            silver_price = round((silver_usd_per_oz * usd_inr) / 31.1035, 2)
    except:
        pass

    return gold_price, silver_price


def get_usd_inr():
    try:
        url = "https://api.exchangerate.host/latest?base=USD&symbols=INR"
        res = requests.get(url, timeout=10)
        data = res.json()
        return round(data["rates"]["INR"], 2)
    except:
        return "N/A"


# ==============================
# NEWS FUNCTIONS
# ==============================
def filter_news(headlines):
    clean_news = []

    for headline in headlines:
        text = headline.lower()

        if "****" in text:
            continue

        if not any(word in text for word in ALLOWED_KEYWORDS):
            continue

        if any(word in text for word in BLOCKED_KEYWORDS):
            continue

        clean_news.append(headline)

    return clean_news[:3]


def get_market_news():
    try:
        url = f"https://newsapi.org/v2/top-headlines?category=business&language=en&apiKey={NEWS_API_KEY}"
        res = requests.get(url, timeout=10)
        data = res.json()

        headlines = []
        for article in data.get("articles", [])[:10]:
            if article.get("title"):
                headlines.append(article["title"])

        news = filter_news(headlines)

        if news:
            return "\n".join([f"• {n}" for n in news])
        else:
            return "📰 No major economic news."

    except:
        return "📰 News unavailable."


# ==============================
# WHATSAPP FUNCTION
# ==============================
def send_whatsapp(message):
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=TWILIO_FROM,
            to=TWILIO_TO
        )
        print("Message SID:", msg.sid)
    except Exception as e:
        print("WhatsApp error:", e)


# ==============================
# MAIN FUNCTION
# ==============================
def main():
    gold, silver = get_gold_silver()
    usd_inr = get_usd_inr()
    news = get_market_news()

    now = datetime.now().strftime("%d %b %Y | %I:%M %p")

    message = f"""
🟡 Gold & Silver Update

Gold: ₹{gold} / g
Silver: ₹{silver} / g
USD/INR: ₹{usd_inr}

📰 Economic News:
{news}

⏰ Time: {now}
"""

    send_whatsapp(message)


if __name__ == "__main__":
    main()


