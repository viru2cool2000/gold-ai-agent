import requests
import os
from datetime import datetime
from twilio.rest import Client

# ==============================
# API KEYS
# ==============================
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# ==============================
# HARD-CODED WHATSAPP NUMBERS
# ==============================
TWILIO_FROM = "whatsapp:+14155238886"
TWILIO_TO = "whatsapp:+919972700255"

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
# PRICE FUNCTIONS (ONLY GOLD-API)
# ==============================
def get_gold_silver():
    gold_price = "N/A"
    silver_price = "N/A"
    usd_inr = None

    # India retail markup
    IMPORT_DUTY = 1.06
    Bank_Charge = 1.005
    Trasport = 135

    TOTAL_MARKUP = IMPORT_DUTY * Bank_Charge

    # Get USD/INR
    try:
        fx = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD",
            timeout=10
        ).json()
        usd_inr = fx["rates"]["INR"]
    except:
        pass

    # Gold price
    try:
        res = requests.get("https://api.gold-api.com/price/XAU", timeout=10)
        data = res.json()
        gold_usd_per_oz = data["price"]

        if usd_inr:
            base_gold = ((gold_usd_per_oz + Transport) * usd_inr) / 31.1035
            gold_price = round(base_gold * TOTAL_MARKUP, 2)
    except:
        pass

    # Silver price
    try:
        res = requests.get("https://api.gold-api.com/price/XAG", timeout=10)
        data = res.json()
        silver_usd_per_oz = data["price"]

        if usd_inr:
            base_silver = (silver_usd_per_oz * usd_inr) / 31.1035
            silver_price = round(base_silver * TOTAL_MARKUP, 2)
    except:
        pass

    return gold_price, silver_price, usd_inr

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
    gold, silver, usd_inr = get_gold_silver()
    news = get_market_news()

    if usd_inr:
        usd_inr_display = round(usd_inr, 2)
    else:
        usd_inr_display = "N/A"

    now = datetime.now().strftime("%d %b %Y | %I:%M %p")

    message = f"""
🟡 Gold & Silver Update

Gold: ₹{gold} / g
Silver: ₹{silver} / g
USD/INR: ₹{usd_inr_display}

📰 Economic News:
{news}

⏰ Time: {now}
"""

    send_whatsapp(message)


if __name__ == "__main__":
    main()





