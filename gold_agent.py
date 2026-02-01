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

def send_whatsapp(message):
    client = Client(TWILIO_SID, TWILIO_AUTH)
    client.messages.create(
        body=message,
        from_=FROM_WHATSAPP,
        to=TO_WHATSAPP
    )

if __name__ == "__main__":
    base_price = get_gold_price()

    IMPORT_DUTY_RATE = 0.06      # 6%
    BANK_CHARGE_RATE = 0.005     # 0.5%

    import_duty = base_price * IMPORT_DUTY_RATE
    bank_charge = base_price * BANK_CHARGE_RATE

    final_indian_price = round(
        base_price + import_duty + bank_charge,
        2
    )

    time_now = datetime.now().strftime("%d %b %Y | %I:%M %p")

    message = (
    "Gold Price Update (India)\n\n"
    f"₹ {final_indian_price} per gram\n\n"
    f"Time: {time_now}\n\n"
    "- Gold AI Agent"
)

    send_whatsapp(message)
