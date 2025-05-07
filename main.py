"""Module for checking holidays and sending equity ban list to Zoho Cliq"""

import logging
import datetime
from urllib3.util.retry import Retry
import requests
from requests.adapters import HTTPAdapter
from zohotok import get_access_token

def setup_logger():
    """Set up the fyers-logger to log messages to a file."""
    fyers_logger = logging.getLogger("fyers-logger")
    fyers_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler("fyerslogger.log")
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    fyers_logger.addHandler(file_handler)

    return fyers_logger

logger = setup_logger()

def is_holiday_today():
    """Check if today is a holiday using the Fyers API."""
    holiday_url = "https://fyers.in/holiday-data.json"
    today = datetime.date.today()

    try:
        response = requests.get(holiday_url, timeout=10)
        response.raise_for_status()
        holiday_data = response.json()

        for holiday in holiday_data:
            holiday_date = datetime.datetime.strptime(
                holiday["holiday_date"], "%B %d, %Y"
            ).date()

            if holiday_date == today:
                segments_closed = holiday.get("segments_closed", [])
                equity_closed = any(
                    segment["segment_name"].lower() == "equity"
                    for segment in segments_closed
                )

                if equity_closed:
                    holiday_name = holiday["holiday_name"]
                    logger.info("Today is a holiday (Equity closed): %s", holiday_name)
                    return True

                logger.info("Today is not a holiday for equity trading.")
                return False

        logger.info("Today is not a holiday.")
        return False

    except requests.exceptions.RequestException as e:
        logger.error("Error fetching holiday data: %s", e)
        raise

def setup_session():
    """Create a session with retry and browser headers for NSE requests."""
    session = requests.Session()

    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/90.0.4430.93 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.nseindia.com/",
        "Connection": "keep-alive"
    })

    # Set homepage cookie to bypass 403 (important for some domains)
    try:
        session.get("https://www.nseindia.com", timeout=5)
    except Exception as e:
        logger.warning("Could not pre-load NSE homepage: %s", e)

    return session

NSE_DOMAIN_MAP = {
    0: "https://archives.nseindia.com/",
    1: "https://nsearchives.nseindia.com/",
    2: "https://www1.nseindia.com/",
}

def fetch_csv_data_with_fallback():
    """Try multiple NSE domains to fetch the CSV."""
    today = datetime.date.today().strftime("%d%m%Y")
    relative_path = f"archives/fo/sec_ban/fo_secban_{today}.csv"
    session = setup_session()

    for domain in NSE_DOMAIN_MAP.values():
        full_url = f"{domain}{relative_path}"
        try:
            logger.info(f"Trying URL: {full_url}")
            response = session.get(full_url, timeout=10)
            response.raise_for_status()
            logger.info("Successfully fetched CSV from %s", full_url)
            return response.text
        except requests.exceptions.RequestException as e:
            logger.warning("Failed to fetch from %s: %s", full_url, e)

    raise Exception("All NSE domains failed to serve the CSV.")

def send_cliq_message(message):
    """Send a message to Zoho Cliq bot and channel."""
    access_token = get_access_token()
    if not access_token:
        logger.error("Failed to retrieve Zoho OAuth token.")
        return False

    bot_url = "https://cliq.zoho.in/company/60006690132/api/v2/bots/watchtower/message"
    channel_url = "https://cliq.zoho.in/api/v2/channelsbyname/csintegrationplayground/message"
    payload = {
        "text": f"### {message}",
        "card": {"title": "ANNOUNCEMENT", "theme": "modern-inline"},
    }
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json",
    }

    try:
        bot_response = requests.post(bot_url, headers=headers, json=payload, timeout=10)
        bot_response.raise_for_status()
        logger.info("Message sent to the bot successfully.")
    except requests.exceptions.RequestException as e:
        logger.error("Failed to send message to the bot: %s", e)
        return False

    try:
        channel_response = requests.post(
            f"{channel_url}?bot_unique_name=watchtower",
            headers=headers,
            json=payload,
            timeout=10,
        )
        channel_response.raise_for_status()
        logger.info("Message sent to the channel successfully.")
    except requests.exceptions.RequestException as e:
        logger.error("Failed to send message to the channel: %s", e)
        return False

    return True

def main():
    """Main function to execute the script."""
    if is_holiday_today():
        logger.info("Skipping script execution as today is a holiday.")
        return

    try:
        raw_csv = fetch_csv_data_with_fallback()
        logger.info("Fetched raw CSV content")
        if send_cliq_message(raw_csv):
            logger.info("Operation completed successfully.")
        else:
            logger.error("Failed to send message to Zoho Cliq.")
    except (requests.exceptions.RequestException, ValueError, Exception) as e:
        logger.error("An error occurred: %s", e)

if __name__ == "__main__":
    main()