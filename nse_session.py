"""Module for managing NSE website sessions to avoid 403 errors."""

import time
import random
import logging
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# NSE URLs
NSE_BASE_URL = "https://www.nseindia.com"
NSE_HOMEPAGE = "https://www.nseindia.com/"

# Browser-like headers - more comprehensive
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="123", "Google Chrome";v="123"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
    "Referer": "https://www.nseindia.com/",
    "Origin": "https://www.nseindia.com",
    "authority": "www.nseindia.com",
    "pragma": "no-cache",
}

# Required NSE cookies (may need to be updated)
NSE_REQUIRED_COOKIES = ['bm_sv', 'ak_bmsc', 'nsit', 'nseappid']

class NSESession:
    """Manages session with NSE website to handle cookies and avoid 403 errors."""
    
    def __init__(self):
        """Initialize the NSE session."""
        self.logger = logging.getLogger("fyers-logger")
        self.session = None
        self.last_request_time = 0
        self.min_request_interval = 2  # Minimum seconds between requests
        self.max_retries = 3  # Maximum number of retries for a request
        
    def _setup_session(self):
        """Set up a new session with retry mechanism and headers."""
        session = requests.Session()
        session.headers.update(NSE_HEADERS)
        session.verify = False  # Disable SSL verification
        
        # Configure retry mechanism
        retry_strategy = Retry(
            total=5,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "HEAD"],
            respect_retry_after_header=True
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _initialize_cookies(self):
        """Initialize cookies by visiting the NSE homepage and market data pages."""
        try:
            # Create a new session
            self.session = self._setup_session()
            
            # First visit the homepage to get initial cookies
            self.logger.info("Visiting NSE homepage to initialize cookies")
            response = self.session.get(NSE_HOMEPAGE, timeout=15)
            response.raise_for_status()
            
            self._log_cookies("After homepage visit")
            
            # Add a delay to mimic human behavior
            time.sleep(2 + random.uniform(0, 1))
            
            # Visit the market data section to get additional cookies
            market_data_url = f"{NSE_BASE_URL}/market-data/securities-available-for-trading"
            self.logger.info(f"Visiting market data page: {market_data_url}")
            response = self.session.get(market_data_url, timeout=15)
            response.raise_for_status()
            
            self._log_cookies("After market data page visit")
            
            # Add another delay
            time.sleep(1 + random.uniform(0, 1))
            
            # Check if we have the required cookies
            if not self._validate_cookies():
                self.logger.warning("Not all required cookies were obtained")
                return False
            
            self.logger.info("Successfully initialized all required cookies")
            return True
            
        except requests.RequestException as e:
            self.logger.error(f"Error initializing NSE session: {str(e)}")
            return False
    
    def _validate_cookies(self):
        """Check if all required cookies are present."""
        if not self.session or not self.session.cookies:
            return False
        
        cookie_dict = {cookie.name: cookie.value for cookie in self.session.cookies}
        missing_cookies = [cookie for cookie in NSE_REQUIRED_COOKIES if cookie not in cookie_dict]
        
        if missing_cookies:
            self.logger.warning(f"Missing required cookies: {missing_cookies}")
            return False
        
        return True
    
    def _log_cookies(self, context=""):
        """Log current cookies for debugging."""
        if not self.session or not self.session.cookies:
            self.logger.info(f"{context}: No cookies available")
            return
        
        cookie_dict = {cookie.name: cookie.value for cookie in self.session.cookies}
        cookie_names = list(cookie_dict.keys())
        self.logger.info(f"{context}: Cookies present: {cookie_names}")
    
    def _log_response_headers(self, response, context=""):
        """Log response headers for debugging."""
        if not response:
            return
        
        self.logger.info(f"{context} Response Headers:")
        for header, value in response.headers.items():
            self.logger.info(f"  {header}: {value}")
    
    def get_session(self):
        """Get an active session with valid cookies."""
        if not self.session or not self.session.cookies or not self._validate_cookies():
            self.logger.info("Session invalid or missing cookies, initializing new session")
            if not self._initialize_cookies():
                self.logger.error("Failed to initialize NSE session")
                return None
        
        return self.session
    
    def get_data(self, url, params=None):
        """Fetch data from NSE with rate limiting and session management."""
        # Rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            self.logger.info(f"Rate limiting: Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        # Add referer specific to the URL being requested
        original_referer = NSE_HEADERS["Referer"]
        headers_update = {
            "Referer": NSE_BASE_URL,
        }
        
        retry_count = 0
        while retry_count < self.max_retries:
            # Get a session
            session = self.get_session()
            if not session:
                return None
            
            # Update headers for this specific request
            session.headers.update(headers_update)
            
            try:
                # Make the request
                self.logger.info(f"Making request to: {url}")
                response = session.get(url, params=params, timeout=15)
                self.last_request_time = time.time()
                
                # If successful, return the response
                if response.status_code == 200:
                    self.logger.info(f"Successfully fetched data from {url}")
                    return response
                
                # If we get a 403 or other error, log headers and retry
                self.logger.warning(f"Got status code {response.status_code} from {url}")
                self._log_response_headers(response, f"Error {response.status_code}")
                
                # Reset session and try again
                self.session = None
                retry_count += 1
                
                if retry_count < self.max_retries:
                    wait_time = 2 ** retry_count + random.uniform(0, 1)
                    self.logger.info(f"Retrying ({retry_count}/{self.max_retries}) in {wait_time:.2f} seconds")
                    time.sleep(wait_time)
                
            except requests.RequestException as e:
                self.logger.error(f"Error fetching data from {url}: {str(e)}")
                self.session = None
                retry_count += 1
                
                if retry_count < self.max_retries:
                    wait_time = 2 ** retry_count + random.uniform(0, 1)
                    self.logger.info(f"Retrying ({retry_count}/{self.max_retries}) in {wait_time:.2f} seconds")
                    time.sleep(wait_time)
                else:
                    return None
        
        self.logger.error(f"Failed to fetch data from {url} after {self.max_retries} retries")
        return None

# Create a global instance for use throughout the application
nse_session = NSESession() 