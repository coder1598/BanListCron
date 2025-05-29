"""Module for checking holidays and send equity banlist to zoho cliq"""

import logging
import datetime
from urllib3.util.retry import Retry
import requests
from requests.adapters import HTTPAdapter
from zohotok import get_access_token
from nse_session import nse_session


def setup_logger():
    """Set up the fyers-logger to log messages to a file."""
    fyers_logger = logging.getLogger("fyers-logger")
    fyers_logger.setLevel(logging.DEBUG)

    # Create file handler to log to a file
    file_handler = logging.FileHandler("fyerslogger.log")
    file_handler.setLevel(logging.DEBUG)

    # Create a formatter for the log messages
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger
    fyers_logger.addHandler(file_handler)
    return fyers_logger


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
                holiday["holiday_date"], "%B %d, %Y"
            ).date()

            if holiday_date == today:
                # Check if equity segment is closed
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
    """Create a requests session with retry logic and browser headers."""
    session = requests.Session()

    # Retry configuration
    retry = Retry(
        total=5,  # Total number of retries
        backoff_factor=1,  # Time between retries will increase exponentially
        status_forcelist=[500, 502, 503, 504],  # Retry for specific status codes
        allowed_methods=["GET", "POST"],  # Retry only GET and POST methods
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Browser headers
    session.headers.update(
        {
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
            "Origin": "https://www.nseindia.com",
        }
    )

    return session


def fetch_csv_data(url):
    """Fetch data from the given URL with error handling and retries."""
    try:
        logger.info("Fetching data from URL: %s", url)
        
        # Use the NSE session manager to get data
        response = nse_session.get_data(url)
        
        if not response:
            logger.error("Failed to get response from NSE")
            raise requests.exceptions.RequestException("Failed to get response from NSE")
        
        # Log successful response info
        logger.info("Response received with status code: %s", response.status_code)
        logger.info("Response content type: %s", response.headers.get('Content-Type', 'unknown'))
        logger.info("Response content length: %s bytes", len(response.content))
        
        # Try to decode the content
        content = response.content.decode('utf-8')
        
        # Check if the content looks like valid CSV data
        first_few_lines = '\n'.join(content.splitlines()[:5])
        logger.info("First few lines of content: %s", first_few_lines)
        
        return content
        
    except requests.exceptions.RequestException as e:
        logger.error("Error fetching data from URL %s: %s", url, e)
        raise
    except UnicodeDecodeError as e:
        logger.error("Unicode decode error: %s. Trying with different encoding...", e)
        try:
            # Try alternate encoding
            content = response.content.decode('latin-1')
            logger.info("Successfully decoded content with latin-1 encoding")
            return content
        except Exception as e2:
            logger.error("Failed to decode with alternate encoding: %s", e2)
            raise ValueError(f"Failed to decode content: {e2}") from e


def send_cliq_message(message):
    """Send a message to Zoho Cliq bot and channel."""
    access_token = get_access_token()
    if not access_token:
        logger.error("Failed to retrieve Zoho OAuth token.")
        return False

    bot_url = "https://cliq.zoho.in/company/60006690132/api/v2/bots/watchtower/message"
    channel_url = (
        "https://cliq.zoho.in/api/v2/channelsbyname/csintegrationplayground/message"
    )
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
        bot_unique_name = "watchtower"
        channel_response = requests.post(
            f"{channel_url}?bot_unique_name={bot_unique_name}",
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

    csv_url = "https://nsearchives.nseindia.com/content/fo/fo_secban.csv"
    try:
        data = fetch_csv_data(csv_url)
        logger.info("Fetched data: %s", data)

        if send_cliq_message(data):
            logger.info("Operation completed succesfully")
        else:
            logger.error("Failed to send message to Zoho Cliq.")
    except (requests.exceptions.RequestException, ValueError) as e:
        logger.error("An error occurred: %s", e)


if __name__ == "__main__":
    main()
