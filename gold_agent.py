import requests
from datetime import datetime
from twilio.rest import Client
import os

# ===== CONFIG =====
GOLD_API_KEY = os.environ.get("GOLD_API_KEY")
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_AUTH = os.environ.get("TWILIO_AUTH")

FROM_WHATSAPP = "whatsapp:+14155238886"   # Twilio sandbox number
TO_WHATSAPP = "whatsapp:+919972700255"    # YOUR WhatsApp number

def get_gold_price():
    url = "https://www.goldapi.io/api/XAU/INR"
    headers = {
        "x-access-token": GOLD_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    data = response.json()

    # CASE 1: API gives price per gram (India format)
    if "price_gram_24k" in data:
        return round(data["price_gram_24k"], 2)

    # CASE 2: API gives price per ounce (international format)
    if "price" in data:
        price_per_gram = data["price"] / 31.1035
        return round(price_per_gram, 2)

    # CASE 3: Something unexpected
    raise Exception(f"Unexpected API response: {data}")
def get_silver_price():
    url = "https://www.goldapi.io/api/XAG/INR"
    headers = {
        "x-access-token": GOLD_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    data = response.json()

    # CASE 1: API gives price per gram
    if "price_gram" in data:
        return round(data["price_gram"], 2)

    # CASE 2: API gives price per ounce
    if "price" in data:
        price_per_gram = data["price"] / 31.1035
        return round(price_per_gram, 2)

    raise Exception(f"Unexpected Silver API response: {data}")


def send_whatsapp(message):
    client = Client(TWILIO_SID, TWILIO_AUTH)
    client.messages.create(
        body=message,
        from_=FROM_WHATSAPP,
        to=TO_WHATSAPP
    )
import requests

NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

def get_gold_relevant_news():
    url = (
        "https://newsapi.org/v2/top-headlines?"
        "category=business&language=en&pageSize=5"
    )
    headers = {"X-Api-Key": NEWS_API_KEY}
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()

    headlines = []
    for a in data.get("articles", []):
        title = a.get("title")
        if title:
            headlines.append(title)
    return headlines
from openai import OpenAI

def ai_gold_bias(headlines):
    if not headlines:
        return "NEUTRAL"

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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

    # Normalize AI output (THIS IS THE KEY PART)
    text = response.output_text.lower()

    if "bullish" in text:
        return "BULLISH"
    if "bearish" in text:
        return "BEARISH"

    return "NEUTRAL"

def read_last_bias():
    try:
        with open("last_bias.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def write_last_bias(bias):
    with open("last_bias.txt", "w") as f:
        f.write(bias)


if __name__ == "__main__":
    # --- PRICE (GOLD) ---
    base_price = get_gold_price()

    IMPORT_DUTY_RATE = 0.06
    BANK_CHARGE_RATE = 0.005

    import_duty = base_price * IMPORT_DUTY_RATE
    bank_charge = base_price * BANK_CHARGE_RATE

    final_indian_price = round(
        base_price + import_duty + bank_charge,
        2
    )

    # --- PRICE (SILVER) ---
    silver_base_price = get_silver_price()

    silver_import_duty = silver_base_price * IMPORT_DUTY_RATE
    silver_bank_charge = silver_base_price * BANK_CHARGE_RATE

    final_silver_price = round(
        silver_base_price + silver_import_duty + silver_bank_charge,
        2
    )

    # --- NEWS + AI ---
    headlines = get_gold_relevant_news()
    current_bias = ai_gold_bias(headlines)

    # --- MEMORY ---
    last_bias = read_last_bias()

    time_now = datetime.now().strftime("%d %b %Y | %I:%M %p")

    # --- FIRST RUN ---
    if last_bias is None:
        write_last_bias(current_bias)
        print("First run. Bias saved:", current_bias)

    # --- BIAS CHANGED ---
    elif current_bias != last_bias:
        key_news = "\n".join(f"• {h}" for h in headlines[:2])

        message = (
            "🚨 Gold AI Alert\n\n"
            "AI Bias Changed:\n"
            f"{last_bias} → {current_bias}\n\n"
            f"Gold:   ₹ {final_indian_price} / gram\n"
            f"Silver: ₹ {final_silver_price} / gram\n\n"
            "Key News:\n"
            f"{key_news}\n\n"
            f"Time: {time_now}\n\n"
            "- Gold AI Agent"
        )

        send_whatsapp(message)
        write_last_bias(current_bias)

    # --- NO CHANGE ---
    else:
        #print("No bias change. Silent run.")

