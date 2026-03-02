from fastapi import FastAPI, Request
from transformers import pipeline
import requests

app = FastAPI()

# Load model once when server starts
classifier = pipeline(
    "zero-shot-classification",
    model="facebook/xlm-roberta-base"
)

VERIFY_TOKEN = "my_verify_token"  # you choose this

@app.get("/webhook")
def verify_webhook(mode: str = None, hub_verify_token: str = None, hub_challenge: str = None):
    if hub_verify_token == VERIFY_TOKEN:
        return int(hub_challenge)
    return "Verification failed"

@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()
    print(data)
    return {"status": "received"}