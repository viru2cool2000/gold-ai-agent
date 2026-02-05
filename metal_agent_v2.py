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
FX_API = "https://open.er-api.com/v6/latest/USD"
METAL_API = "https://api.gold-api.com/price"

# -------------------------------
# WHATSAPP (TWILIO)
# -------------------------------
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# Hardcoded sandbox numbers (temporary)
FROM_WHATSAPP = "whatsapp:+14155238886"
TO_WHATSAPP = "whatsapp:+919972700255"

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

WHATSAPP_ENABLED = True


# -------------------------------
# WHATSAPP SENDER
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
# METAL FETCH (simple test)
# -------------------------------
def get_usd_to_inr():
    r = requests.get(FX_API, timeout=10)
    r.raise_for_status()
    return r.json()["rates"]["INR"]


def get_gold_price_inr():
    fx = get_usd_to_inr()
    r = requests.get(f"{METAL_API}/XAU", timeout=10)
    r.raise_for_status()
    price_usd = r.json()["price"]
    return round(price_usd * fx, 2)


# -------------------------------
# GITHUB SINGLE RUN (TEST)
# -------------------------------
def run_once():
    try:
        gold_price = get_gold_price_inr()
        send_whatsapp(f"🧪 GitHub Test OK\nGold price (oz): ₹{gold_price}")
    except Exception as e:
        send_whatsapp(f"❌ Test failed: {str(e)}")


# -------------------------------
# START
# -------------------------------
if __name__ == "__main__":
    run_once()
