from fastapi import FastAPI, Request
import os
import requests
from transformers import pipeline
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Timer

app = FastAPI()

# ==============================
# ENV VARIABLES
# ==============================
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
MOM_NUMBER = os.getenv("MOM_NUMBER")  # Without +

# ==============================
# AI MODEL
# ==============================
classifier = pipeline(
    "zero-shot-classification",
    model="facebook/xlm-roberta-base"
)

def classify_reply(text):
    labels = ["took medicine", "did not take medicine"]
    result = classifier(text, labels)
    return result["labels"][0]

# ==============================
# WHATSAPP SEND FUNCTION
# ==============================
def send_whatsapp_message(to, text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }

    requests.post(url, headers=headers, json=data)

# ==============================
# STATE TRACKING
# ==============================
awaiting_reply = False
awaiting_image = False

# ==============================
# FOLLOW-UP FUNCTION
# ==============================
def send_followup():
    global awaiting_reply
    if awaiting_reply:
        send_whatsapp_message(
            MOM_NUMBER,
            "Ammi ❤️ please confirm about your medicine."
        )

# ==============================
# MORNING REMINDER
# ==============================
def morning_reminder():
    global awaiting_reply, awaiting_image
    awaiting_reply = True
    awaiting_image = False

    send_whatsapp_message(
        MOM_NUMBER,
        "Good morning ❤️ Did you take your medicine?"
    )

    # 1 hour later reminder
    Timer(3600, send_followup).start()

# ==============================
# SCHEDULER
# ==============================
scheduler = BackgroundScheduler(timezone="Asia/Karachi")
scheduler.add_job(
    morning_reminder,
    "cron",
    hour=8,
    minute=0
)
scheduler.start()

# ==============================
# WEBHOOK VERIFY
# ==============================
@app.get("/webhook")
def verify_webhook(hub_mode: str = None,
                   hub_verify_token: str = None,
                   hub_challenge: str = None):
    if hub_verify_token == VERIFY_TOKEN:
        return int(hub_challenge)
    return "Verification failed"

# ==============================
# WEBHOOK RECEIVE
# ==============================
@app.post("/webhook")
async def receive_message(request: Request):
    global awaiting_reply, awaiting_image

    data = await request.json()
    print("Incoming:", data)

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        sender = message["from"]
        message_type = message["type"]

        # ===== IMAGE RECEIVED =====
        if message_type == "image":
            awaiting_reply = False
            awaiting_image = False

            send_whatsapp_message(
                sender,
                "Thank you ❤️ Medicine confirmed."
            )
            return {"status": "image confirmed"}

        # ===== TEXT RECEIVED =====
        if message_type == "text":
            text = message["text"]["body"]

            awaiting_reply = False

            label = classify_reply(text)

            if label == "took medicine":
                awaiting_image = True
                send_whatsapp_message(
                    sender,
                    "Please send a picture ❤️"
                )
            else:
                send_whatsapp_message(
                    sender,
                    "Please take it soon ❤️"
                )

    except Exception as e:
        print("Error:", e)

    return {"status": "processed"}