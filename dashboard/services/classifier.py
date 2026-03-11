import requests
import json
from config import OLLAMA_URL, OLLAMA_MODEL

def classify_email(subject: str, sender: str, body: str) -> dict:
    prompt = f'''Analyze this email and respond ONLY with valid JSON.
Required fields:
- category: one of [useful, spam, newsletter, work, personal, other]
- priority: one of [high, medium, low]
- summary: max 30 words summary in italian
- action_required: true or false

Email:
Sender: {sender}
Subject: {subject}
Body: {body[:1000]}

Respond ONLY with JSON, no other text, no markdown, no backticks.
'''
    response = requests.post(OLLAMA_URL, json={
        'model': OLLAMA_MODEL,
        'prompt': prompt,
        'stream': False
    })
    raw = response.json()['response'].strip()
    raw = raw.replace('```json', '').replace('```', '').strip()
    return json.loads(raw)
