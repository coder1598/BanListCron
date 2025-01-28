def is_holiday_today():
    """Check if today is a holiday using the NSE API."""
    nse_holiday_url = "https://www.nseindia.com/api/holiday-master?type=trading"
    today = datetime.date.today()
    session = setup_session()  # Use the existing session setup with headers and retry logic

    # Adding necessary headers to simulate a browser request
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Referer": "https://www.nseindia.com/",
        "Origin": "https://www.nseindia.com",
        "X-Requested-With": "XMLHttpRequest"  # Simulate AJAX request
    })

    try:
        # Fetch holiday data from the NSE API with payload type=trading
        response = session.get(nse_holiday_url, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses (e.g., 4xx, 5xx)
        
        # Log the response headers and status code for debugging
        logger.info("Response status code: %s", response.status_code)
        logger.info("Response headers: %s", response.headers)

        # If the response is compressed, decompress it
        if 'gzip' in response.headers.get('Content-Encoding', ''):
            buf = io.BytesIO(response.content)
            f = gzip.GzipFile(fileobj=buf)
            decompressed_data = f.read().decode('utf-8')  # Decode as UTF-8
        else:
            decompressed_data = response.text  # Use the text as is if not compressed

        # Parse the decompressed response as JSON
        try:
            holiday_data = response.json()  # Try parsing the response as JSON
        except ValueError as e:
            logger.error("Error parsing JSON from response: %s", e)
            logger.error("Raw response body: %s", decompressed_data)
            return False

        # Log the holiday data structure for verification
        logger.info("Holiday data structure: %s", holiday_data)

        # Check if 'CBM' key exists and look for today's date
        if 'CBM' in holiday_data:
            for holiday in holiday_data['CBM']:
                holiday_date = datetime.datetime.strptime(holiday["tradingDate"], "%d-%b-%Y").date()
                if holiday_date == today:
                    holiday_name = holiday["description"]
                    logger.info("Today is a holiday: %s", holiday_name)
                    print(f"Today is a holiday: {holiday_name}")
                    return True

        print("Today is not a holiday.")
        return False
    except requests.exceptions.RequestException as e:
        logger.error("Error fetching NSE holiday data: %s", e)
        raise
