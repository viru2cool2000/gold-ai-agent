import requests
from datetime import datetime, timezone, timedelta
from twilio.rest import Client
import os
from openai import OpenAI

# ===== CONFIG =====
GOLD_API_KEY = os.environ.get("GOLD_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_AUTH = os.environ.get("TWILIO_AUTH")

AGENT_NAME = "Viru AI"

FROM_WHATSAPP = "whatsapp:+14155238886"
TO_WHATSAPP = "whatsapp:+919972700255"

# ===== PRICE FUNCTIONS =====
def get_gold_price():
    url = "https://www.goldapi.io/api/XAU/INR"
    headers = {
        "x-access-token": GOLD_API_KEY,
        "Content-Type": "application/json"
    }
    r = requests.get(url, headers=headers, timeout=10)
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

    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()

        if "price_gram" in data:
            return round(data["price_gram"], 2)

        if "price" in data:
            return round(data["price"] / 31.1035, 2)

    except:
        pass

    # 🔁 Fallback to free API
    return get_silver_price_fallback()
def get_silver_price_fallback():
    try:
        url = "https://api.metals.live/v1/spot"
        r = requests.get(url, timeout=10)
        data = r.json()

        # data example: [["silver", 23.45], ["gold", 2034.1]]
        for item in data:
            if item[0].lower() == "silver":
                # Convert USD/oz → INR/gram approx
                usd_per_oz = item[1]
                usd_to_inr = 83  # approx rate, acceptable for fallback
                return round((usd_per_oz * usd_to_inr) / 31.1035, 2)
    except:
        pass

    return None



# ===== WHATSAPP =====
def send_whatsapp(message):
    client = Client(TWILIO_SID, TWILIO_AUTH)
    client.messages.create(
        body=message,
        from_=FROM_WHATSAPP,
        to=TO_WHATSAPP
    )

# ===== NEWS =====
MACRO_KEYWORDS = [
    "gold", "silver", "inflation", "interest rate", "fed",
    "dollar", "usd", "trade deal", "tariff", "us india",
    "geopolitical", "economy", "recession"
]

def get_gold_relevant_news():
    url = (
        "https://newsapi.org/v2/top-headlines?"
        "category=business&language=en&pageSize=10"
    )
    headers = {"X-Api-Key": NEWS_API_KEY}
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()

    macro_news = []
    fallback_news = []

    for a in data.get("articles", []):
        title = a.get("title", "")
        if not title:
            continue

        fallback_news.append(title)

        if any(k.lower() in title.lower() for k in MACRO_KEYWORDS):
            macro_news.append(title)

    if macro_news:
        return macro_news[:2]
    elif fallback_news:
        return [fallback_news[0]]
    else:
        return ["Markets await fresh economic cues; gold trades in a narrow range."]

# ===== AI ANALYSIS =====
def ai_gold_analysis(headlines):
    if not OPENAI_API_KEY:
        return {
            "bias": "NEUTRAL",
            "confidence": 0.50
        }

    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = (
        "You are a gold market analyst.\n"
        "Based on the headlines below, decide gold bias:\n"
        "Bullish, Slightly Bullish, Neutral, Slightly Bearish, or Bearish.\n\n"
        "Respond ONLY with the bias word.\n\n"
        + "\n".join(f"- {h}" for h in headlines)
    )

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        max_output_tokens=20
    )

    text = response.output_text.lower()

    if "slightly bearish" in text:
        bias = "SLIGHTLY BEARISH"
    elif "bearish" in text:
        bias = "BEARISH"
    elif "slightly bullish" in text:
        bias = "SLIGHTLY BULLISH"
    elif "bullish" in text:
        bias = "BULLISH"
    else:
        bias = "NEUTRAL"

    confidence_map = {
        "BULLISH": 0.70,
        "BEARISH": 0.70,
        "SLIGHTLY BULLISH": 0.60,
        "SLIGHTLY BEARISH": 0.60,
        "NEUTRAL": 0.50
    }

    return {
        "bias": bias,
        "confidence": confidence_map[bias]
    }

# ===== MAIN =====
if __name__ == "__main__":
    gold_base = get_gold_price()
    silver_base = get_silver_price()

    IMPORT_DUTY = 0.06
    BANK_CHARGE = 0.005

    gold_price = round(gold_base * (1 + IMPORT_DUTY + BANK_CHARGE), 2)
    silver_price = round(silver_base * (1 + IMPORT_DUTY + BANK_CHARGE), 2)

    headlines = get_gold_relevant_news()
    analysis = ai_gold_analysis(headlines)

    news_text = "• " + "\n• ".join(headlines[:2])

    IST = timezone(timedelta(hours=5, minutes=30))
    time_now = datetime.now(IST).strftime("%d %b %Y | %I:%M %p")

    message = (
        "🤖 Viru AI\n"
        "🟡 Gold Rate Update\n\n"
        f"Gold: ₹{gold_price} / g\n"
        f"Silver: ₹{silver_price} / g\n\n"
        f"AI Bias: {analysis['bias']}\n"
        f"Confidence: {analysis['confidence']}\n\n"
        "📰 News Highlights:\n"
        f"{news_text}\n\n"
        f"⏰ Time: {time_now}"
    )

    send_whatsapp(message)

