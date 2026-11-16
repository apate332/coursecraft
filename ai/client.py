import os

import requests
import streamlit as st
from dotenv import load_dotenv


# =========================================================
# LOCAL ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# ASU AI CONFIGURATION
# =========================================================

API_URL = "https://api-main.aiml.asu.edu/query"


def get_api_key():
    """
    Get the ASU AI API key.

    Local development:
        Reads ASU_AI_API_KEY from .env

    Streamlit Community Cloud:
        Reads ASU_AI_API_KEY from Streamlit Secrets
    """

    # -----------------------------------------------------
    # STREAMLIT CLOUD / STREAMLIT SECRETS
    # -----------------------------------------------------

    try:
        if "ASU_AI_API_KEY" in st.secrets:
            return st.secrets["ASU_AI_API_KEY"]

    except Exception:
        pass

    # -----------------------------------------------------
    # LOCAL .ENV
    # -----------------------------------------------------

    api_key = os.getenv(
        "ASU_AI_API_KEY"
    )

    if api_key:
        return api_key

    # -----------------------------------------------------
    # NOTHING FOUND
    # -----------------------------------------------------

    raise ValueError(
        "ASU_AI_API_KEY is not configured. "
        "For local development, add it to .env. "
        "For deployment, add it to Streamlit Secrets."
    )


# =========================================================
# ASU AI REQUEST
# =========================================================

def ask_asu_ai(prompt):

    api_key = get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
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