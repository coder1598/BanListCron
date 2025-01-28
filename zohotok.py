import os
import logging

import requests


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Load environment variables (provided by GitHub Secrets)
CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ZOHO_REDIRECT_URI", "http://localhost:3002/callback")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")  # Provided via GitHub Secrets


def get_access_token():
    """Generate an access token using the refresh token."""
    if not REFRESH_TOKEN:
        logging.error(
            "Refresh token is not set. Please check the ZOHO_REFRESH_TOKEN "
            "environment variable."
        )
        return None

    token_url = "https://accounts.zoho.in/oauth/v2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }

    try:
        response = requests.post(token_url, data=data, timeout=10)
        response.raise_for_status()  # Raise an error for HTTP codes >= 400
        token_data = response.json()

        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)  # Default expiry time

        if not access_token:
            logging.error(
                f"Failed to retrieve access token. Response: {token_data}"
            )
            return None

        logging.info(
            f"Access token retrieved successfully. Expires in {expires_in} "
            "seconds."
        )
        return access_token
    except requests.RequestException as e:
        logging.error(f"Error fetching access token: {e}")
        return None


# Example usage
if __name__ == "__main__":
    token = get_access_token()
    if token:
        logging.info(f"Access Token: {token}")