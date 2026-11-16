import os

import requests
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("ASU_AI_API_KEY")
API_URL = "https://api-main.aiml.asu.edu/query"


def ask_asu_ai(prompt):
    if not API_KEY:
        raise ValueError("ASU_AI_API_KEY was not found in .env")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "query": prompt,
    }

    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=120,
    )

    response.raise_for_status()

    return response.json()