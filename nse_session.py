"""Module for managing NSE website sessions to avoid 403 errors."""

import time
import random
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# NSE URLs
NSE_BASE_URL = "https://www.nseindia.com"
NSE_HOMEPAGE = "https://www.nseindia.com/"

# Browser-like headers
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "sec-ch-ua": '"Google Chrome";v="91", "Chromium";v="91", ";Not A Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
    "Referer": "https://www.nseindia.com/",
}

class NSESession:
    """Manages session with NSE website to handle cookies and avoid 403 errors."""
    
    def __init__(self):
        """Initialize the NSE session."""
        self.logger = logging.getLogger("fyers-logger")
        self.session = None
        self.last_request_time = 0
        self.min_request_interval = 1  # Minimum seconds between requests
        
    def _setup_session(self):
        """Set up a new session with retry mechanism and headers."""
        session = requests.Session()
        session.headers.update(NSE_HEADERS)
        session.verify = False  # Disable SSL verification
        
        # Configure retry mechanism
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _initialize_cookies(self):
        """Initialize cookies by visiting the NSE homepage."""
        try:
            # Create a new session
            self.session = self._setup_session()
            
            # Visit the homepage to get cookies
            response = self.session.get(NSE_HOMEPAGE, timeout=10)
            response.raise_for_status()
            
            # Add a small delay to mimic human behavior
            time.sleep(1 + random.uniform(0, 1))
            
            if not self.session.cookies:
                self.logger.error("Failed to get cookies from NSE homepage")
                return False
            
            self.logger.info("Successfully initialized cookies from NSE homepage")
            return True
            
        except requests.RequestException as e:
            self.logger.error(f"Error initializing NSE session: {e}")
            return False
            
    def get_session(self):
        """Get an active session with valid cookies."""
        if not self.session or not self.session.cookies:
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
            time.sleep(sleep_time)
        
        # Get a session
        session = self.get_session()
        if not session:
            return None
        
        try:
            # Make the request
            response = session.get(url, params=params, timeout=10)
            self.last_request_time = time.time()
            
            # Check if we're getting blocked or need to refresh cookies
            if response.status_code in [403, 401]:
                self.logger.warning(f"Got status code {response.status_code}, refreshing session")
                self.session = None
                time.sleep(2)  # Wait a bit before trying again
                
                # Try once more with a fresh session
                session = self.get_session()
                if not session:
                    return None
                    
                response = session.get(url, params=params, timeout=10)
                self.last_request_time = time.time()
            
            response.raise_for_status()
            return response
            
        except requests.RequestException as e:
            self.logger.error(f"Error fetching data from {url}: {e}")
            return None

# Create a global instance for use throughout the application
nse_session = NSESession() 