import requests
from datetime import datetime
from twilio.rest import Client
import os
from openai import OpenAI

# ===== CONFIG =====
GOLD_API_KEY = os.environ.get("GOLD_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_AUTH = os.environ.get("TWILIO_AUTH")

FROM_WHATSAPP = "whatsapp:+14155238886"
TO_WHATSAPP = "whatsapp:+919972700255"


# ===== PRICE FUNCTIONS =====
def get_gold_price():
    url = "https://www.goldapi.io/api/XAU/INR"
    headers = {
        "x-access-token": GOLD_API_KEY,
        "Content-Type": "application/json"
    }
    r = requests.get(url, headers=headers)
    data = r.json()

    if "price_gram_24k" in data:
        return round(data["price_gram_24k"], 2)

    if "price" in data:
        return round(data["price"] / 31.1035, 2)

    raise Exception(data)


def get_silver_price():
    url = "https://www.goldapi.io/api/XAG/INR"
    headers = {
        "x-access-token": GOLD_API_KEY,
        "Content-Type": "application/json"
    }
    r = requests.get(url, headers=headers)
    data = r.json()

    if "price_gram" in data:
        return round(data["price_gram"], 2)

    if "price" in data:
        return round(data["price"] / 31.1035, 2)

    raise Exception(data)


# ===== WHATSAPP =====
def send_whatsapp(message):
    client = Client(TWILIO_SID, TWILIO_AUTH)
    client.messages.create(
        body=message,
        from_=FROM_WHATSAPP,
        to=TO_WHATSAPP
    )


# ===== NEWS + AI =====
def get_gold_relevant_news():
    url = (
        "https://newsapi.org/v2/top-headlines?"
        "category=business&language=en&pageSize=5"
    )
    headers = {"X-Api-Key": NEWS_API_KEY}
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()

    return [a["title"] for a in data.get("articles", []) if a.get("title")]


def ai_gold_bias(headlines):
    if not headlines:
        return "NEUTRAL"

    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = (
        "You are a commodities analyst. "
        "Based on these headlines, decide gold price bias "
        "(bullish, bearish, or neutral). Respond briefly.\n\n"
        + "\n".join(f"- {h}" for h in headlines)
    )

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        max_output_tokens=30
    )

    text = response.output_text.lower()

    if "bullish" in text:
        return "BULLISH"
    if "bearish" in text:
        return "BEARISH"
    return "NEUTRAL"


# ===== MAIN =====
if __name__ == "__main__":
    gold_base = get_gold_price()
    silver_base = get_silver_price()

    IMPORT_DUTY = 0.06
    BANK_CHARGE = 0.005

    gold_price = round(gold_base * (1 + IMPORT_DUTY + BANK_CHARGE), 2)
    silver_price = round(silver_base * (1 + IMPORT_DUTY + BANK_CHARGE), 2)

    headlines = get_gold_relevant_news()
    bias = ai_gold_bias(headlines)
    
    news_text = "• " + "\n• ".join(headlines[:2]) if headlines else "No major gold-related news."

    from datetime import datetime, timezone, timedelta

    IST = timezone(timedelta(hours=5, minutes=30))
    time_now = datetime.now(IST).strftime("%d %b %Y | %I:%M %p")

    message = (
    "🟡 Gold Market Update\n\n"
    f"Gold: ₹{gold_price} / g\n"
    f"Silver: ₹{silver_price} / g\n\n"
    f"AI Bias: {bias}\n\n"
    "📰 News Highlights:\n"
    f"{news_text}\n\n"
    f"Time: {time_now}"
)

    send_whatsapp(message)


