import os
import time

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


API_URL = "https://api-main.aiml.asu.edu/query"

CONNECT_TIMEOUT = 30
READ_TIMEOUT = 180
MAX_ATTEMPTS = 3


def get_api_key():
    """
    Get the ASU AI API key.

    Local:
        ASU_AI_API_KEY from .env

    Streamlit Cloud:
        ASU_AI_API_KEY from Streamlit Secrets
    """

    # Streamlit Cloud
    try:
        if "ASU_AI_API_KEY" in st.secrets:
            api_key = st.secrets[
                "ASU_AI_API_KEY"
            ]

            if api_key:
                return str(api_key)

    except Exception:
        pass

    # Local development
    api_key = os.getenv(
        "ASU_AI_API_KEY"
    )

    if api_key:
        return api_key

    raise ValueError(
        "ASU_AI_API_KEY is not configured. "
        "For local development, add it to .env. "
        "For deployment, add it to Streamlit Secrets."
    )


def ask_asu_ai(prompt):
    """
    Send a prompt to ASU AI.

    Automatically retries temporary timeouts and
    server/network failures.
    """

    api_key = get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "query": prompt,
    }

    last_error = None

    for attempt in range(
        1,
        MAX_ATTEMPTS + 1,
    ):

        try:

            response = requests.post(
                API_URL,
                headers=headers,
                json=payload,
                timeout=(
                    CONNECT_TIMEOUT,
                    READ_TIMEOUT,
                ),
            )

            response.raise_for_status()

            return response.json()

        except (
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
        ) as error:

            last_error = error

            if attempt < MAX_ATTEMPTS:

                # Short increasing delay:
                # attempt 1 -> 3 sec
                # attempt 2 -> 6 sec
                time.sleep(
                    attempt * 3
                )

                continue

        except requests.exceptions.HTTPError as error:

            last_error = error

            status_code = (
                error.response.status_code
                if error.response is not None
                else None
            )

            # Retry temporary server failures.
            if (
                status_code is not None
                and status_code >= 500
                and attempt < MAX_ATTEMPTS
            ):

                time.sleep(
                    attempt * 3
                )

                continue

            raise RuntimeError(
                "ASU AI returned an HTTP error. "
                f"Status: {status_code}"
            ) from error

        except requests.exceptions.RequestException as error:

            last_error = error
            break

    raise RuntimeError(
        "ASU AI did not respond after "
        f"{MAX_ATTEMPTS} attempts. "
        "This is usually a temporary service or "
        "network delay. Please try again."
    ) from last_error