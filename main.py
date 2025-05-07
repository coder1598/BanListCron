import logging
import datetime
import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from zohotok import get_access_token

TEMP_FILE_PATH = "/tmp/secban.csv"
MAX_RETRY_COUNT = 3
SLEEP_TIME = 3
REQUEST_TIMEOUT = 10

REQ_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Priority': 'u=0, i',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
    'Content-Type': 'application/json'
}

NSE_DOMAIN_MAP = {
    0: "https://archives.nseindia.com/",
    1: "https://nsearchives.nseindia.com/",
    2: "https://www1.nseindia.com/",
}

def setup_logger():
    logger = logging.getLogger("fyers-logger")
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler("fyerslogger.log")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = setup_logger()

def is_holiday_today():
    today = datetime.date.today()
    url = "https://fyers.in/holiday-data.json"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        holidays = resp.json()
        for h in holidays:
            h_date = datetime.datetime.strptime(h["holiday_date"], "%B %d, %Y").date()
            if h_date == today:
                if any(s["segment_name"].lower() == "equity" for s in h.get("segments_closed", [])):
                    logger.info(f"Today is a holiday: {h['holiday_name']}")
                    return True
        logger.info("Today is not a holiday.")
        return False
    except Exception as e:
        logger.error("Error checking holiday: %s", e)
        return False

def download_csv_file():
    today_str = datetime.date.today().strftime("%d%m%Y")
    rel_path = f"archives/fo/sec_ban/fo_secban_{today_str}.csv"

    session = requests.Session()

    # Use the working NSE_CM_BHAV_HEADERS
    HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0"
    }

    session.headers.update(HEADERS)

    # Step 1: Warm-up request to set cookies
    try:
        home = session.get("https://www.nseindia.com", timeout=5)
        session.cookies.update(home.cookies)  # Apply any returned cookies
        logger.info("NSE homepage warmed up.")
    except Exception as e:
        logger.warning("Warm-up request failed: %s", e)

    for _, domain in NSE_DOMAIN_MAP.items():
        url = f"{domain}{rel_path}"
        logger.info(f"Trying to download: {url}")
        for attempt in range(MAX_RETRY_COUNT):
            try:
                response = session.get(url, timeout=REQUEST_TIMEOUT)
                if response.status_code == 200:
                    with open(TEMP_FILE_PATH, "wb") as f:
                        f.write(response.content)
                    logger.info("File downloaded successfully to %s", TEMP_FILE_PATH)
                    return TEMP_FILE_PATH
                else:
                    logger.warning(f"Attempt {attempt+1}: Got status code {response.status_code}")
                    time.sleep(SLEEP_TIME)
            except Exception as e:
                logger.warning(f"Attempt {attempt+1}: Failed to download file - {e}")
                time.sleep(SLEEP_TIME)
    raise Exception("Failed to download CSV from all fallback domains.")

def parse_csv(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error("Failed to read CSV file: %s", e)
        raise

def send_cliq_message(message):
    access_token = get_access_token()
    if not access_token:
        logger.error("Zoho token not available")
        return False

    bot_url = "https://cliq.zoho.in/company/60006690132/api/v2/bots/watchtower/message"
    channel_url = "https://cliq.zoho.in/api/v2/channelsbyname/csintegrationplayground/message"
    payload = {
        "text": f"### {message}",
        "card": {"title": "ANNOUNCEMENT", "theme": "modern-inline"},
    }
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }

    try:
        requests.post(bot_url, headers=headers, json=payload, timeout=10).raise_for_status()
        requests.post(f"{channel_url}?bot_unique_name=watchtower", headers=headers, json=payload, timeout=10).raise_for_status()
        logger.info("Message sent successfully to Zoho Cliq.")
        return True
    except Exception as e:
        logger.error("Error sending message to Cliq: %s", e)
        return False

def main():
    if is_holiday_today():
        logger.info("Skipping: Today is a holiday.")
        return

    try:
        file_path = download_csv_file()
        csv_text = parse_csv(file_path)
        if send_cliq_message(csv_text):
            logger.info("All operations completed successfully.")
        else:
            logger.error("Failed to send to Zoho Cliq.")
    except Exception as e:
        logger.error("Main execution error: %s", e)

if __name__ == "__main__":
    main()