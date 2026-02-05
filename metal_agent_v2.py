from twilio.rest import Client

# 🔴 PASTE YOUR REAL TWILIO CREDENTIALS HERE
TWILIO_ACCOUNT_SID = "AC6d657d2ade6b37954d9d988173427ff0"
TWILIO_AUTH_TOKEN = "77e365e12011665c1383653a2ca277b4"

# Twilio WhatsApp sandbox
FROM_WHATSAPP = "whatsapp:+14155238886"
TO_WHATSAPP = "whatsapp:+919972700255"

def test_whatsapp():
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        message = client.messages.create(
            body="🚨 WhatsApp trigger test from GitHub",
            from_=FROM_WHATSAPP,
            to=TO_WHATSAPP
        )

        print("Message SID:", message.sid)

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    test_whatsapp()
