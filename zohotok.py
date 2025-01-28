import os
import json
import time
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables (provided by GitHub Secrets)
CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ZOHO_REDIRECT_URI", "http://localhost:3002/callback")  # Default fallback
TOKEN_FILE = os.getenv("ZOHO_TOKEN_FILE", "zohotoken.json")
REFRESH_THRESHOLD_SECONDS = 300  # Refresh 5 minutes before expiry

# Helper functions
def load_tokens():
    """Load tokens from the environment or a local file."""
    token_data = os.getenv("ZOHO_TOKEN_DATA")
    if token_data:
        try:
            return json.loads(token_data)
        except json.JSONDecodeError:
            logging.error("Environment variable ZOHO_TOKEN_DATA contains invalid JSON.")
            return None

    if not os.path.exists(TOKEN_FILE):
        logging.error(f"Token file {TOKEN_FILE} does not exist.")
        return None

    try:
        with open(TOKEN_FILE, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:
        logging.error(f"Token file {TOKEN_FILE} is invalid or empty.")
        return None

def save_tokens(tokens):
    """Save tokens to the environment or a local file."""
    token_data = os.getenv("ZOHO_TOKEN_DATA")
    if token_data is not None:
        # Tokens are stored in the environment; updating is not possible
        logging.warning("Token data is managed via environment variables. Changes will not persist.")
        return

    try:
        with open(TOKEN_FILE, "w") as file:
            json.dump(tokens, file, indent=4)
        logging.info(f"Tokens successfully saved to {TOKEN_FILE}.")
    except IOError as e:
        logging.error(f"Failed to write to token file {TOKEN_FILE}: {str(e)}")

# Core functionality
def refresh_access_token():
    """Refresh the access token using the refresh token."""
    tokens = load_tokens()
    if not tokens or "refresh_token" not in tokens:
        logging.error("No refresh token found. Please authenticate first.")
        return

    refresh_token = tokens["refresh_token"]
    token_url = "https://accounts.zoho.in/oauth/v2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    }

    try:
        response = requests.post(token_url, data=data, timeout=10)
        if response.status_code == 200:
            new_tokens = response.json()
            access_token = new_tokens.get("access_token")
            expires_in = new_tokens.get("expires_in", 3600)  # Default to 3600 seconds
            expiry_time = time.time() + expires_in

            tokens.update({
                "access_token": access_token,
                "expires_in": expires_in,
                "expiry_time": expiry_time,
            })
            save_tokens(tokens)
            logging.info("Access token refreshed successfully.")
        else:
            logging.error(f"Failed to refresh token. Status: {response.status_code}, Response: {response.text}")
    except requests.RequestException as e:
        logging.error(f"Error refreshing token: {str(e)}")

def check_token_expiry():
    """Check if the access token is near expiry and refresh if needed."""
    tokens = load_tokens()
    if not tokens or "expiry_time" not in tokens:
        logging.error("No token or expiry time found. Please authenticate.")
        return

    expiry_time = tokens["expiry_time"]
    time_left = expiry_time - time.time()

    if time_left < REFRESH_THRESHOLD_SECONDS:
        logging.info(f"Access token will expire in {time_left:.2f} seconds. Refreshing token...")
        refresh_access_token()
    else:
        logging.info(f"Access token is valid for another {time_left:.2f} seconds.")

def get_access_token():
    """Get the current access token, refreshing it if necessary."""
    tokens = load_tokens()
    if not tokens:
        logging.error("No tokens found. Please authenticate.")
        return None

    access_token = tokens.get("access_token")
    expiry_time = tokens.get("expiry_time", 0)

    if time.time() > expiry_time:
        logging.info("Access token expired. Refreshing token...")
        refresh_access_token()
        tokens = load_tokens()  # Reload tokens after refresh
        access_token = tokens.get("access_token")

    if not access_token:
        logging.error("Failed to retrieve a valid access token.")

    return access_token

# Example usage
if __name__ == "__main__":
    try:
        # Ensure token is refreshed if necessary
        check_token_expiry()

        # Get access token for API requests
        token = get_access_token()
        if token:
            logging.info(f"Access token retrieved successfully: {token}")
        else:
            logging.error("Failed to retrieve access token.")
    except Exception as e:
        logging.exception(f"Unexpected error occurred: {str(e)}")
