import logging
import datetime
from urllib3.util.retry import Retry

import requests
from requests.adapters import HTTPAdapter

from zohotok import get_access_token


def setup_logger():
    """Set up the fyers-logger to log messages to a file."""
    logger = logging.getLogger("fyers-logger")
    logger.setLevel(logging.DEBUG)

    # Create file handler to log to a file
    file_handler = logging.FileHandler("fyerslogger.log")
    file_handler.setLevel(logging.DEBUG)

    # Create a formatter for the log messages
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger
    logger.addHandler(file_handler)
    return logger


# Set up the logger
logger = setup_logger()


def is_holiday_today():
    """Check if today is a holiday using the Fyers API."""
    holiday_url = "https://fyers.in/holiday-data.json"
    today = datetime.date.today()
    try:
        response = requests.get(holiday_url, timeout=10)
        response.raise_for_status()
        holiday_data = response.json()

        # Extract and parse holiday dates
        for holiday in holiday_data:
            holiday_date = datetime.datetime.strptime(
                holiday['holiday_date'], "%B %d, %Y"
            ).date()
            if holiday_date == today:
                holiday_name = holiday['holiday_name']
                logger.info("Today is a holiday: %s", holiday_name)
                print(f"Today is a holiday: {holiday_name}")
                return True
        print("Today is not a holiday.")
        return False
    except requests.exceptions.RequestException as e:
        logger.error("Error fetching holiday data: %s", e)
        raise


def setup_session():
    """Create a requests session with retry logic and browser headers."""
    session = requests.Session()

    # Retry configuration
    retry = Retry(
        total=5,  # Total number of retries
        backoff_factor=1,  # Time between retries will increase exponentially
        status_forcelist=[500, 502, 503, 504],  # Retry for specific status codes
        allowed_methods=["GET", "POST"]  # Retry only GET and POST methods
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Browser headers
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                  "image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "Referer": "https://www.nseindia.com/",
        "Origin": "https://www.nseindia.com"
    })

    return session


def fetch_csv_data(url):
    """Fetch data from the given URL with error handling and retries."""
    session = setup_session()

    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses
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
    channel_url = "https://cliq.zoho.in/api/v2/channelsbyname/supportteam/message"
    payload = {
        "text": f"### {message}",
        "card": {
            "title": "ANNOUNCEMENT",
            "theme": "modern-inline"
        }
    }
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    try:
        bot_response = requests.post(bot_url, headers=headers, json=payload)
        bot_response.raise_for_status()
        logger.info("Message sent to the bot successfully.")
    except requests.exceptions.RequestException as e:
        logger.error("Failed to send message to the bot: %s", e)
        return False
    try:
        bot_unique_name = "watchtower"
        channel_response = requests.post(
            f"{channel_url}?bot_unique_name={bot_unique_name}",
            headers=headers,
            json=payload
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

    csv_url = "https://nsearchives.nseindia.com/content/fo/fo_secban.csv"
    try:
        data = fetch_csv_data(csv_url)
        logger.info("Fetched data: %s", data)

        if send_cliq_message(data):
            logger.info("Message sent to Zoho Cliq successfully.")
        else:
            logger.error("Failed to send message to Zoho Cliq.")
    except Exception as e:
        logger.error("An error occurred: %s", e)


if __name__ == "__main__":
    main()
