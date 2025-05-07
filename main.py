import logging
import datetime
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from zohotok import get_access_token

def setup_logger():
    """Set up the fyers-logger to log messages to a file."""
    fyers_logger = logging.getLogger("fyers-logger")
    fyers_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler("fyerslogger.log")
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
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
                    logger.info("Today is a holiday (Equity closed): %s", holiday["holiday_name"])
                    return True

                logger.info("Today is not a holiday for equity trading.")
                return False

        logger.info("Today is not a holiday.")
        return False

    except requests.exceptions.RequestException as e:
        logger.error("Error fetching holiday data: %s", e)
        raise

def setup_session():
    """Create a session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def fetch_csv_data(url):
    """Fetch NSE CSV data with session and headers."""
    session = setup_session()

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'Referer': 'https://www.nseindia.com',
    }

    try:
        # Step 1: Get cookies by visiting homepage
        session.get("https://www.nseindia.com", headers=headers, timeout=10)

        # Step 2: Access the CSV URL
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.content.decode("utf-8")

    except requests.exceptions.RequestException as e:
        logger.error("Error fetching data from URL %s: %s", url, e)
        raise

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
    """Main execution flow."""
    if is_holiday_today():
        logger.info("Skipping execution as today is a holiday.")
        return

    csv_url = "https://nsearchives.nseindia.com/content/fo/fo_secban.csv"
    try:
        data = fetch_csv_data(csv_url)
        logger.info("Fetched data: %s", data)

        if send_cliq_message(data):
            logger.info("Operation completed successfully.")
        else:
            logger.error("Failed to send message to Zoho Cliq.")
    except (requests.exceptions.RequestException, ValueError) as e:
        logger.error("An error occurred: %s", e)

if __name__ == "__main__":
    main()