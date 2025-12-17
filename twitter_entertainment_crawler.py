"""
🐦 TWITTER ENTERTAINMENT CRAWLER - Using Selenium/BeautifulSoup
Crawl Twitter/X data for sentiment analysis on entertainment (films/music)

TÍNH NĂNG:
✅ Scrape tweets về films và music
✅ Lọc chỉ English tweets
✅ Extract engagement metrics (likes, retweets, replies)
✅ Support multiple search modes (keywords, hashtags, users, trends)
✅ Filter by date range
✅ Export to CSV/JSON
✅ Integrate with data_cleaner

CÁCH SỬ DỤNG:
python twitter_entertainment_crawler.py

LƯU Ý:
- Cần cài đặt Chrome/Chromium và ChromeDriver
- Có thể cần đăng nhập Twitter để tránh rate limiting
- Sử dụng Selenium để handle dynamic content
- BeautifulSoup để parse HTML và extract data
"""

import json
import logging
import os
import random
import re
import time
import getpass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote_plus

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Setup logging
from logger_config import get_main_logger
logger = get_main_logger()

# Import data cleaner
from data_cleaner import CommentDataCleaner


class TwitterEntertainmentCrawler:
    """
    Twitter/X Crawler chuyên dụng cho entertainment sentiment analysis
    Sử dụng Selenium để scrape dynamic content và BeautifulSoup để parse HTML
    
    Fields collected (optimized for sentiment analysis):
    - comment_text: Tweet content (cleaned)
    - author_name: Username
    - author_id: User ID
    - published_at: Timestamp
    - like_count: Number of likes
    - retweet_count: Number of retweets
    - reply_count: Number of replies
    - quote_count: Number of quote tweets
    - platform: "Twitter"
    - tweet_id: Unique tweet ID
    - language: "en" (English only)
    - entertainment_category: "film" or "music"
    - hashtags: List of hashtags
    - mentions: List of mentions
    - urls: List of URLs in tweet
    - media_type: Type of media (photo, video, etc.)
    - is_reply: Boolean (is this a reply?)
    - parent_tweet_id: Parent tweet ID (if reply)
    - sentiment_label: NULL (to be filled by sentiment analysis)
    - sentiment_score: NULL (to be filled by sentiment analysis)
    """
    
    # Entertainment-related keywords and hashtags
    FILM_KEYWORDS = [
        '#movie', '#film', '#cinema', '#movies', '#films',
        'movie review', 'film review', 'box office', 'Oscar', 'Oscars',
        'new movie', 'best movie', 'movie trailer', 'film festival'
    ]
    
    MUSIC_KEYWORDS = [
        '#music', '#song', '#songs', '#album', '#albums',
        '#musician', '#singer', '#artist', '#spotify', '#billboard',
        'new album', 'new song', 'music review', 'top charts',
        'Grammy', 'Grammys', 'music video', 'single release'
    ]
    
    # English language detection pattern
    ENGLISH_PATTERN = re.compile(r'[a-zA-Z]+')
    
    # Rate limiting configuration (IMPORTANT: To avoid being blocked)
    DEFAULT_DELAY_BETWEEN_REQUESTS = 2.0  # seconds between requests
    MIN_DELAY = 1.0  # minimum delay
    MAX_DELAY = 5.0  # maximum delay for randomization
    DELAY_AFTER_BATCH = 5.0  # delay after every N tweets
    BATCH_SIZE = 50  # process in batches
    MAX_RETRIES = 3  # retry on failure
    RETRY_DELAY = 10.0  # delay before retry
    
    def __init__(self, delay_between_requests: float = None, 
                 use_random_delays: bool = True,
                 batch_size: int = None,
                 headless: bool = True,
                 driver_path: Optional[str] = None,
                 use_firefox: bool = False,
                 use_undetected: bool = False,
                 output_folder: str = "twitter_entertainment",
                 debug_mode: bool = False,
                 sort_by: str = "latest"):
        """
        Initialize crawler
        
        Args:
            delay_between_requests: Delay between requests (seconds)
            use_random_delays: Use random delays to avoid pattern detection
            batch_size: Number of tweets to process before longer delay
            headless: Run browser in headless mode
            driver_path: Path to ChromeDriver (None = auto-detect)
            use_firefox: Use Firefox instead of Chrome (better anti-detection)
            use_undetected: Use undetected-chromedriver (requires: pip install undetected-chromedriver)
            output_folder: Folder name inside 'data/' to save scraped data (default: "twitter_entertainment")
            debug_mode: Enable debug mode (save screenshots and HTML for debugging)
            sort_by: Sort tweets by 'latest' or 'top' (top = high engagement)
        """
        self.cleaner = CommentDataCleaner()
        self.crawled_data = []
        self.driver = None
        self.headless = headless
        self.driver_path = driver_path
        self.use_firefox = use_firefox
        self.use_undetected = use_undetected
        self.output_folder = output_folder
        self.debug_mode = debug_mode
        self.sort_by = sort_by  # 'latest' or 'top'
        self.session_cookies = []  # Store cookies in memory only (not persisted)
        
        # Create debug folder if debug mode enabled
        if self.debug_mode:
            self.debug_folder = Path("debug_output")
            self.debug_folder.mkdir(exist_ok=True)
            logger.info(f"🐛 DEBUG MODE ENABLED - outputs will be saved to {self.debug_folder}/")
        
        # Rate limiting settings
        self.delay_between_requests = delay_between_requests or self.DEFAULT_DELAY_BETWEEN_REQUESTS
        self.use_random_delays = use_random_delays
        self.batch_size = batch_size or self.BATCH_SIZE
        
        logger.info("TwitterEntertainmentCrawler initialized (Selenium/BeautifulSoup)")
        logger.info(f"Rate limiting: delay={self.delay_between_requests}s, random={use_random_delays}, batch_size={self.batch_size}")
        logger.info(f"Browser mode: {'headless' if headless else 'visible'}")
        logger.info("🔒 Session-based cookies: Cookies sẽ chỉ tồn tại trong phiên làm việc này")
    
    def _setup_driver(self):
        """Setup Selenium WebDriver with anti-detection measures"""
        if self.driver:
            return
        
        # Option 1: Use undetected-chromedriver (best anti-detection)
        if self.use_undetected:
            try:
                import undetected_chromedriver as uc
                logger.info("Using undetected-chromedriver for better anti-detection...")
                
                # Check version if possible
                try:
                    version = getattr(uc, '__version__', 'unknown')
                    logger.info(f"undetected-chromedriver version: {version}")
                except:
                    pass
                
                # undetected-chromedriver API is different from regular selenium
                # It auto-detects Chrome and downloads matching driver automatically
                # IMPORTANT: undetected-chromedriver manages its own driver
                # We must NOT pass driver_path or driver_executable_path
                
                # Create ChromeOptions (must be fresh, cannot reuse)
                options = uc.ChromeOptions()
                if self.headless:
                    options.add_argument('--headless=new')
                else:
                    options.add_argument('--start-maximized')
                
                # Additional options for better anti-detection
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                
                # undetected-chromedriver completely auto-detects and manages driver
                # Do NOT pass driver_executable_path or any driver-related parameters
                # It will automatically:
                # 1. Detect Chrome version
                # 2. Download matching ChromeDriver
                # 3. Patch it to avoid detection
                # 4. Initialize browser
                
                # Try multiple initialization methods (version compatibility)
                init_success = False
                last_error = None
                
                # Method 1: Simple initialization (no use_subprocess)
                try:
                    logger.debug("Trying Method 1: Simple initialization...")
                    self.driver = uc.Chrome(options=options)
                    logger.info("✅ Undetected ChromeDriver initialized successfully (Method 1)!")
                    init_success = True
                except Exception as e1:
                    logger.debug(f"Method 1 failed: {e1}")
                    last_error = e1
                
                # Method 2: Without options
                if not init_success:
                    try:
                        logger.debug("Trying Method 2: Without options...")
                        self.driver = uc.Chrome()
                        logger.info("✅ Undetected ChromeDriver initialized successfully (Method 2)!")
                        init_success = True
                    except Exception as e2:
                        logger.debug(f"Method 2 failed: {e2}")
                        last_error = e2
                
                # Method 3: With use_subprocess
                if not init_success:
                    try:
                        logger.debug("Trying Method 3: With use_subprocess...")
                        self.driver = uc.Chrome(options=options, use_subprocess=True)
                        logger.info("✅ Undetected ChromeDriver initialized successfully (Method 3)!")
                        init_success = True
                    except Exception as e3:
                        logger.debug(f"Method 3 failed: {e3}")
                        last_error = e3
                
                # Method 4: Specify headless explicitly in Chrome() call
                if not init_success:
                    try:
                        logger.debug("Trying Method 4: With headless parameter...")
                        simple_options = uc.ChromeOptions()
                        if not self.headless:
                            simple_options.add_argument('--start-maximized')
                        self.driver = uc.Chrome(
                            options=simple_options,
                            headless=self.headless
                        )
                        logger.info("✅ Undetected ChromeDriver initialized successfully (Method 4)!")
                        init_success = True
                    except Exception as e4:
                        logger.debug(f"Method 4 failed: {e4}")
                        last_error = e4
                
                # If all methods failed, raise error
                if not init_success:
                    error_str = str(last_error).lower() if last_error else ''
                    error_msg = str(last_error) if last_error else 'Unknown error'
                    
                    logger.error(f"❌ All initialization methods failed!")
                    logger.error(f"   Last error: {error_msg}")
                    logger.error("")
                    logger.error("🔧 TROUBLESHOOTING:")
                    logger.error("   1. Check Chrome is installed:")
                    logger.error("      macOS: /Applications/Google Chrome.app")
                    logger.error("      Windows: C:\\Program Files\\Google\\Chrome")
                    logger.error("")
                    logger.error("   2. Upgrade undetected-chromedriver:")
                    logger.error("      pip install --upgrade undetected-chromedriver")
                    logger.error("")
                    logger.error("   3. Try different version:")
                    logger.error("      pip install undetected-chromedriver==3.5.0")
                    logger.error("")
                    logger.error("   4. Or use Firefox (option 2) - usually works better")
                    
                    raise last_error
                
                logger.info("Undetected ChromeDriver ready for use")
                
                # Load session cookies if available
                if self.session_cookies:
                    self._load_session_cookies()
                return
            except ImportError:
                logger.error("❌ undetected-chromedriver not installed!")
                logger.error("   Install with: pip install undetected-chromedriver")
                logger.warning("Falling back to regular ChromeDriver...")
            except Exception as e:
                logger.error(f"❌ Failed to initialize undetected-chromedriver: {e}")
                logger.error("   This is critical - undetected-chromedriver is needed to avoid Twitter detection")
                logger.error("   Regular ChromeDriver will likely be blocked by Twitter")
                logger.warning("Falling back to regular ChromeDriver (may not work)...")
                import traceback
                logger.debug(traceback.format_exc())
        
        # Option 2: Use Firefox (often less detected than ChromeDriver)
        if self.use_firefox:
            try:
                from selenium.webdriver import Firefox
                from selenium.webdriver.firefox.options import Options as FirefoxOptions
                from selenium.webdriver.firefox.service import Service as FirefoxService
                
                logger.info("Using Firefox for better anti-detection...")
                
                firefox_options = FirefoxOptions()
                if self.headless:
                    firefox_options.add_argument('--headless')
                
                firefox_options.set_preference("general.useragent.override", 
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0")
                
                if self.driver_path:
                    service = FirefoxService(executable_path=self.driver_path)
                    self.driver = Firefox(service=service, options=firefox_options)
                else:
                    self.driver = Firefox(options=firefox_options)
                
                logger.info("Firefox WebDriver initialized successfully")
                
                # Load session cookies if available
                if self.session_cookies:
                    self._load_session_cookies()
                return
            except ImportError:
                logger.warning("Firefox WebDriver not available. Install geckodriver")
                logger.warning("Falling back to ChromeDriver...")
            except Exception as e:
                logger.warning(f"Failed to initialize Firefox: {e}")
                logger.warning("Falling back to ChromeDriver...")
        
        # Option 3: Regular ChromeDriver with enhanced anti-detection
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless=new')  # Use new headless mode
        
        # Basic options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Anti-detection: Remove automation indicators
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("detach", True)
        
        # Use realistic user agent (match your system)
        import platform
        if platform.system() == "Darwin":  # macOS
            user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        elif platform.system() == "Windows":
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        else:  # Linux
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        options.add_argument(f'--user-agent={user_agent}')
        
        # Additional anti-detection measures
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--lang=en-US,en')
        
        # Window size (make it look like real browser)
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        
        # Disable automation flags
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            from selenium.webdriver.chrome.service import Service
            if self.driver_path:
                service = Service(executable_path=self.driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
            
            # Execute JavaScript to hide webdriver property
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.navigator.chrome = {
                        runtime: {},
                    };
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });
                '''
            })
            
            # Additional CDP commands to avoid detection
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": user_agent,
                "platform": platform.system(),
                "acceptLanguage": "en-US,en;q=0.9"
            })
            
            logger.info("ChromeDriver initialized successfully with anti-detection measures")
            
            # Load session cookies if available
            if self.session_cookies:
                self._load_session_cookies()
        except Exception as e:
            logger.error(f"Failed to initialize ChromeDriver: {e}")
            raise RuntimeError("ChromeDriver not found. Please install ChromeDriver or set driver_path.")
    
    def _load_session_cookies(self):
        """Load cookies from session memory"""
        if not self.session_cookies:
            logger.debug("No session cookies to load")
            return
            
        try:
            self.driver.get("https://twitter.com")
            time.sleep(2)
            
            for cookie in self.session_cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Error adding cookie: {e}")
            
            logger.info(f"✅ Loaded {len(self.session_cookies)} session cookies from memory")
            
            # IMPORTANT: Refresh page to apply cookies
            logger.debug("Refreshing page to apply cookies...")
            self.driver.refresh()
            time.sleep(3)
            
            # Verify cookies were applied
            try:
                page_source = self.driver.page_source.lower()
                if 'login' not in page_source and 'sign in' not in page_source:
                    logger.info("✅ Session cookies applied - user is logged in")
                else:
                    logger.warning("⚠️ Session cookies may have expired")
            except Exception as e:
                logger.debug(f"Could not verify cookie status: {e}")
                
        except Exception as e:
            logger.warning(f"Failed to load session cookies: {e}")
    
    def save_session_cookies(self):
        """Save current cookies to session memory (not file)"""
        if not self.driver:
            logger.warning("Driver not initialized. Cannot save cookies.")
            return False
        
        try:
            self.session_cookies = self.driver.get_cookies()
            logger.info(f"✅ Saved {len(self.session_cookies)} cookies to session memory")
            logger.debug("Cookies will be available during this session only")
            return True
        except Exception as e:
            logger.error(f"Failed to save session cookies: {e}")
            return False
    
    def manual_login(self, timeout: int = 300):
        """
        Manual login - open browser and let user login manually
        
        Args:
            timeout: Maximum time to wait for user to complete login (seconds, default=300)
        
        Returns:
            bool: True if login successful, False otherwise
        """
        if not self.driver:
            self._setup_driver()
        
        try:
            logger.info("Opening Twitter login page...")
            self.driver.get("https://twitter.com/i/flow/login")
            time.sleep(2)
            
            logger.info("=" * 70)
            logger.info("🔐 MANUAL LOGIN MODE")
            logger.info("=" * 70)
            logger.info("Vui lòng đăng nhập thủ công trong browser window")
            logger.info("Sau khi login thành công, cookies sẽ được tự động lưu")
            logger.info(f"Bạn có {timeout} giây để hoàn thành login")
            logger.info("=" * 70)
            
            print("\n" + "=" * 70)
            print("🔐 MANUAL LOGIN")
            print("=" * 70)
            print("✋ Vui lòng đăng nhập trong browser window đã mở")
            print(f"⏱️  Thời gian tối đa: {timeout} giây")
            print("✅ Sau khi login xong, cookies sẽ được lưu tự động")
            print("🔄 Đang chờ login...")
            print("=" * 70)
            
            # Wait for user to login
            start_time = time.time()
            check_interval = 2
            max_checks = timeout // check_interval
            
            for check_count in range(max_checks):
                try:
                    current_url = self.driver.current_url
                    page_source = self.driver.page_source.lower()
                    page_title = self.driver.title.lower()
                    
                    # Check if logged in (not on login page anymore)
                    if 'login' not in current_url.lower() and 'flow' not in current_url.lower():
                        if 'home' in current_url.lower() or 'twitter.com/home' in current_url or 'x.com/home' in current_url:
                            logger.info("✅ Login successful!")
                            self.save_session_cookies()
                            return True
                    
                    # Check for login indicators in page
                    if 'sign in' not in page_source and 'log in' not in page_source:
                        if 'home' in page_source or 'timeline' in page_source:
                            if 'login' not in page_title and 'sign in' not in page_title:
                                logger.info("✅ Login successful!")
                                self.save_session_cookies()
                                return True
                    
                    # Log progress every 30 seconds
                    elapsed = check_count * check_interval
                    if elapsed > 0 and elapsed % 30 == 0:
                        remaining = timeout - elapsed
                        logger.info(f"⏱️  Còn {remaining} giây... Vui lòng login trong browser")
                        print(f"⏱️  Còn {remaining} giây...")
                    
                except Exception as e:
                    logger.debug(f"Error checking login status: {e}")
                
                time.sleep(check_interval)
            
            logger.warning("⚠️ Login timeout. User did not complete login in time.")
            return False
            
        except Exception as e:
            logger.error(f"Error during manual login: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def auto_login(self, username: str, password: str, timeout: int = 60):
        """
        Automatic login with username and password
        
        Args:
            username: Twitter username or email
            password: Twitter password
            timeout: Maximum time to wait for each step (seconds)
        
        Returns:
            bool: True if login successful, False otherwise
        """
        if not self.driver:
            self._setup_driver()
        
        # Ensure browser is visible for login (user may need to handle 2FA)
        if self.headless:
            logger.warning("⚠️ Headless mode is ON. Switching to visible mode for login.")
            logger.warning("   User may need to handle 2FA or verification manually.")
            # Note: Can't change headless after driver is created, but we'll log warning
        
        try:
            logger.info("Opening Twitter login page...")
            self.driver.get("https://twitter.com/i/flow/login")
            time.sleep(3)
            
            # Step 1: Enter username/email
            logger.info("Entering username/email...")
            try:
                # Try multiple selectors for username input
                username_selectors = [
                    'input[autocomplete="username"]',
                    'input[name="text"]',
                    'input[type="text"]',
                    'input[data-testid="ocfEnterTextTextInput"]'
                ]
                
                username_input = None
                for selector in username_selectors:
                    try:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        # Check if element is actually found and visible
                        if element and (hasattr(element, 'is_displayed') and element.is_displayed() or not hasattr(element, 'is_displayed')):
                            username_input = element
                            logger.debug(f"Found username input with selector: {selector}")
                            break
                    except (TimeoutException, NoSuchElementException, AttributeError) as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                if not username_input:
                    logger.error("Could not find username input field")
                    logger.error("Possible reasons:")
                    logger.error("  1. Page structure has changed")
                    logger.error("  2. Page hasn't loaded completely")
                    logger.error("  3. Twitter requires additional verification")
                    logger.error("   Please check the browser window")
                    return False
                
                # Wait for element to be clickable
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(username_input)
                    )
                except TimeoutException:
                    logger.warning("Username input not clickable, trying anyway...")
                
                # Re-find element to avoid stale reference
                try:
                    username_input = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, username_selectors[0]))
                    )
                except:
                    pass  # Use existing element if re-find fails
                
                try:
                    username_input.clear()
                    time.sleep(0.5)
                    
                    # Type slowly to mimic human behavior
                    for char in username:
                        try:
                            username_input.send_keys(char)
                            time.sleep(random.uniform(0.1, 0.3))
                        except Exception as e:
                            # Re-find element if stale
                            logger.debug(f"Stale element, re-finding: {e}")
                            username_input = WebDriverWait(self.driver, 3).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, username_selectors[0]))
                            )
                            username_input.send_keys(char)
                            time.sleep(random.uniform(0.1, 0.3))
                    
                    time.sleep(random.uniform(1, 2))
                    
                    # Click Next button
                    next_selectors = [
                        'button[data-testid="ocfEnterTextNextButton"]',
                        'div[role="button"][data-testid="ocfEnterTextNextButton"]',
                        'button:contains("Next")',
                        'div[role="button"]:contains("Next")'
                    ]
                    
                    next_button = None
                    for selector in next_selectors:
                        try:
                            if ':contains' in selector:
                                # Use XPath for text contains
                                next_button = self.driver.find_element(By.XPATH, "//div[@role='button' and contains(text(), 'Next')]")
                            else:
                                next_button = WebDriverWait(self.driver, 5).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                            break
                        except (TimeoutException, NoSuchElementException):
                            continue
                    
                    if next_button:
                        next_button.click()
                        time.sleep(3)  # Wait longer for page transition
                    else:
                        # Try pressing Enter
                        username_input.send_keys(Keys.RETURN)
                        time.sleep(3)
                except Exception as e:
                    logger.warning(f"Error during username input: {e}, trying to continue...")
                    time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error entering username: {e}")
                return False
            
            # Step 2: Check for unusual activity (phone verification, username verification, etc.)
            time.sleep(2)  # Wait for page to update after clicking Next
            page_source = self.driver.page_source.lower()
            current_url = self.driver.current_url.lower()
            
            # Check if Twitter asks to verify username again (unusual activity)
            if any(keyword in page_source for keyword in ['unusual activity', 'verify your identity', 'confirm it\'s you', 'enter your phone']):
                logger.warning("⚠️ Twitter requires verification (unusual activity check)")
                logger.warning("   Twitter may ask you to:")
                logger.warning("   1. Verify username again")
                logger.warning("   2. Enter phone number")
                logger.warning("   3. Complete CAPTCHA")
                logger.warning("   Please complete verification manually in the browser")
                logger.warning("   Waiting 60 seconds for manual verification...")
                
                # Wait and check if user completes verification
                start_wait = time.time()
                while time.time() - start_wait < 60:
                    time.sleep(2)
                    try:
                        current_page = self.driver.page_source.lower()
                        current_url_check = self.driver.current_url.lower()
                        # Check if moved past verification
                        if 'password' in current_page or 'login' not in current_url_check:
                            logger.info("Verification appears complete, continuing...")
                            break
                    except:
                        pass
                
                # Check if still on verification page
                page_source = self.driver.page_source.lower()
                if any(keyword in page_source for keyword in ['unusual activity', 'verify your identity', 'confirm it\'s you']):
                    logger.warning("Still on verification page. Please complete verification manually.")
                    logger.warning("Waiting additional 30 seconds...")
                    time.sleep(30)
            
            # Step 3: Enter password
            logger.info("Entering password...")
            try:
                password_selectors = [
                    'input[name="password"]',
                    'input[type="password"]',
                    'input[autocomplete="current-password"]',
                    'input[data-testid="ocfEnterTextTextInput"]'
                ]
                
                password_input = None
                for selector in password_selectors:
                    try:
                        element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        # Check if element is actually found
                        if element and (hasattr(element, 'is_displayed') and element.is_displayed() or not hasattr(element, 'is_displayed')):
                            password_input = element
                            logger.debug(f"Found password input with selector: {selector}")
                            break
                    except (TimeoutException, NoSuchElementException, AttributeError) as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                if not password_input:
                    logger.error("Could not find password input field")
                    logger.warning("Twitter may require additional verification. Check browser.")
                    logger.warning("   Possible reasons:")
                    logger.warning("   1. Phone verification required")
                    logger.warning("   2. Unusual activity check")
                    logger.warning("   3. Page structure changed")
                    return False
                
                # Wait for element to be clickable
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(password_input)
                    )
                except TimeoutException:
                    logger.warning("Password input not clickable, trying anyway...")
                
                # Re-find element to avoid stale reference
                try:
                    password_input = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, password_selectors[0]))
                    )
                except:
                    pass  # Use existing element if re-find fails
                
                try:
                    password_input.clear()
                    time.sleep(0.5)
                    
                    # Type slowly to mimic human behavior
                    for char in password:
                        try:
                            password_input.send_keys(char)
                            time.sleep(random.uniform(0.1, 0.2))
                        except Exception as e:
                            # Re-find element if stale
                            logger.debug(f"Stale element, re-finding: {e}")
                            password_input = WebDriverWait(self.driver, 3).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, password_selectors[0]))
                            )
                            password_input.send_keys(char)
                            time.sleep(random.uniform(0.1, 0.2))
                    
                    time.sleep(random.uniform(1, 2))
                except Exception as e:
                    logger.warning(f"Error during password input: {e}, trying to continue...")
                    time.sleep(2)
                
                # Click Log in button
                login_selectors = [
                    'button[data-testid="LoginForm_Login_Button"]',
                    'button[data-testid="ocfEnterTextNextButton"]',
                    'div[role="button"][data-testid="LoginForm_Login_Button"]',
                    'button:contains("Log in")',
                    'div[role="button"]:contains("Log in")'
                ]
                
                login_button = None
                for selector in login_selectors:
                    try:
                        if ':contains' in selector:
                            login_button = self.driver.find_element(By.XPATH, "//div[@role='button' and contains(text(), 'Log in')]")
                        else:
                            login_button = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                        break
                    except (TimeoutException, NoSuchElementException):
                        continue
                
                if login_button:
                    login_button.click()
                else:
                    # Try pressing Enter
                    password_input.send_keys(Keys.RETURN)
                
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"Error entering password: {e}")
                return False
            
            # Step 4: Check for 2FA or additional verification
            page_source = self.driver.page_source.lower()
            if 'two-factor' in page_source or '2fa' in page_source or 'verification code' in page_source:
                logger.warning("⚠️ Twitter requires 2FA verification")
                logger.warning("   Please enter 2FA code manually in the browser")
                logger.warning("   Waiting 60 seconds for 2FA input...")
                time.sleep(60)
            
            # Step 5: Wait for login to complete and check success
            logger.info("Waiting for login to complete...")
            start_time = time.time()
            check_interval = 2
            max_checks = timeout // check_interval
            
            for check_count in range(max_checks):
                try:
                    current_url = self.driver.current_url
                    page_source = self.driver.page_source.lower()
                    page_title = self.driver.title.lower()
                    
                    # Check for "could not log you in" error immediately
                    if 'could not log you in' in page_source or 'please try again later' in page_source:
                        logger.error("❌ Login failed: Twitter blocked login attempt")
                        logger.error("   Error message: 'Could not log you in now. Please try again later.'")
                        logger.error("   This usually means:")
                        logger.error("   1. Twitter detected automation/bot")
                        logger.error("   2. Rate limiting or IP flagging")
                        logger.error("   3. Account security check")
                        logger.error("   4. Too many login attempts")
                        logger.error("   Solutions:")
                        logger.error("   - Wait 15-30 minutes before trying again")
                        logger.error("   - Try from different IP/network")
                        logger.error("   - Use Firefox or Undetected ChromeDriver")
                        logger.error("   - Try manual login in regular browser")
                        logger.error("   - Check if account is locked/suspended")
                        return False
                    
                    # Check if logged in (not on login page anymore)
                    if 'login' not in current_url.lower() and 'flow' not in current_url.lower():
                        if 'home' in current_url.lower() or 'twitter.com/home' in current_url or 'x.com/home' in current_url:
                            logger.info("✅ Login successful!")
                            self.save_session_cookies()
                            return True
                    
                    # Check for login indicators in page
                    if 'sign in' not in page_source and 'log in' not in page_source:
                        if 'home' in page_source or 'timeline' in page_source or 'twitter.com' in current_url or 'x.com' in current_url:
                            if 'login' not in page_title and 'sign in' not in page_title:
                                logger.info("✅ Login successful!")
                                self.save_session_cookies()
                                return True
                    
                    # Check for other error messages
                    error_messages = [
                        ('incorrect', 'wrong password', '❌ Login failed: Incorrect username or password'),
                        ('suspended', 'locked', '❌ Login failed: Account may be suspended or locked'),
                    ]
                    
                    for error_keywords, error_msg in error_messages:
                        if any(kw in page_source for kw in error_keywords):
                            logger.error(error_msg)
                            return False
                    
                    # Log progress every 10 checks
                    if check_count % 10 == 0 and check_count > 0:
                        logger.debug(f"Still waiting for login... ({check_count * check_interval}s elapsed)")
                    
                except Exception as e:
                    logger.debug(f"Error checking login status: {e}")
                    # Continue checking
                
                time.sleep(check_interval)
            
            logger.warning("⚠️ Login timeout. May require manual verification.")
            logger.warning("   Check browser for any additional steps needed.")
            return False
            
        except Exception as e:
            logger.error(f"Error during auto login: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def _close_driver(self):
        """Close Selenium WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("ChromeDriver closed")
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")
    
    def _save_debug_info(self, step_name: str):
        """
        Save debug information (screenshot + HTML) for troubleshooting
        
        Args:
            step_name: Name of the current step (e.g., 'after_login', 'search_page')
        """
        if not self.debug_mode or not self.driver:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_base = f"{timestamp}_{step_name}"
            
            # Save screenshot
            screenshot_path = self.debug_folder / f"{filename_base}.png"
            self.driver.save_screenshot(str(screenshot_path))
            logger.info(f"🐛 Screenshot saved: {screenshot_path}")
            
            # Save HTML
            html_path = self.debug_folder / f"{filename_base}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info(f"🐛 HTML saved: {html_path}")
            
            # Save current URL
            url_path = self.debug_folder / f"{filename_base}_url.txt"
            with open(url_path, 'w', encoding='utf-8') as f:
                f.write(f"URL: {self.driver.current_url}\n")
                f.write(f"Title: {self.driver.title}\n")
            logger.info(f"🐛 URL info saved: {url_path}")
            
        except Exception as e:
            logger.warning(f"Failed to save debug info: {e}")
    
    def _get_random_delay(self) -> float:
        """Get random delay to avoid pattern detection"""
        if self.use_random_delays:
            return random.uniform(self.MIN_DELAY, self.MAX_DELAY)
        return self.delay_between_requests
    
    def _smart_delay(self, tweet_count: int):
        """
        Apply smart delay strategy:
        - Small delay after each tweet
        - Longer delay after batches
        - Random delays to avoid detection
        """
        if tweet_count % self.batch_size == 0 and tweet_count > 0:
            # Longer delay after batch
            delay = self.DELAY_AFTER_BATCH + random.uniform(0, 3.0)
            logger.debug(f"Batch delay: {delay:.2f}s after {tweet_count} tweets")
            time.sleep(delay)
        else:
            # Normal delay with randomization
            delay = self._get_random_delay()
            time.sleep(delay)
    
    def is_english_text(self, text: str) -> bool:
        """
        Check if text is primarily English
        
        Args:
            text: Text to check
            
        Returns:
            bool: True if text is primarily English
        """
        if not text:
            return False
        
        # Count English characters
        english_chars = len(self.ENGLISH_PATTERN.findall(text))
        total_chars = len(re.sub(r'\s', '', text))
        
        if total_chars == 0:
            return False
        
        # At least 70% English characters
        english_ratio = english_chars / total_chars if total_chars > 0 else 0
        return english_ratio >= 0.7
    
    def extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        hashtags = re.findall(r'#\w+', text)
        return [h.lower() for h in hashtags]
    
    def extract_mentions(self, text: str) -> List[str]:
        """Extract mentions from text"""
        mentions = re.findall(r'@\w+', text)
        return [m.lower() for m in mentions]
    
    def extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text"""
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        return url_pattern.findall(text)
    
    def detect_entertainment_category(self, text: str, hashtags: List[str]) -> Optional[str]:
        """
        Detect if tweet is about film or music
        
        Args:
            text: Tweet text
            hashtags: List of hashtags
            
        Returns:
            'film', 'music', or None
        """
        text_lower = text.lower()
        
        # Film indicators
        film_keywords = ['movie', 'film', 'cinema', 'actor', 'actress', 'director', 
                        'trailer', 'box office', 'oscar', 'hollywood', 'premiere']
        film_hashtags = ['#movie', '#film', '#cinema', '#movies', '#films', '#oscar']
        
        # Music indicators
        music_keywords = ['song', 'album', 'music', 'artist', 'singer', 'musician',
                         'spotify', 'billboard', 'grammy', 'single', 'release', 'track']
        music_hashtags = ['#music', '#song', '#album', '#spotify', '#billboard', '#grammy']
        
        # Check text
        film_score = sum(1 for kw in film_keywords if kw in text_lower)
        music_score = sum(1 for kw in music_keywords if kw in text_lower)
        
        # Check hashtags
        film_score += sum(1 for ht in film_hashtags if ht in hashtags)
        music_score += sum(1 for ht in music_hashtags if ht in hashtags)
        
        # Determine category
        if film_score > music_score and film_score > 0:
            return 'film'
        elif music_score > film_score and music_score > 0:
            return 'music'
        else:
            return None  # Could be both or neither
    
    def _parse_tweet_element(self, tweet_element) -> Optional[Dict]:
        """
        Parse a tweet HTML element using BeautifulSoup
        
        Args:
            tweet_element: BeautifulSoup element or Selenium WebElement
            
        Returns:
            Dict with tweet data or None if invalid
        """
        try:
            # Convert to BeautifulSoup if it's a Selenium element
            if hasattr(tweet_element, 'get_attribute'):
                html = tweet_element.get_attribute('outerHTML')
                soup = BeautifulSoup(html, 'html.parser')
            else:
                soup = tweet_element
            
            # Extract tweet text
            tweet_text_elem = soup.find('div', {'data-testid': 'tweetText'})
            if not tweet_text_elem:
                # Try alternative selectors
                tweet_text_elem = soup.find('div', class_=re.compile(r'.*tweet.*text.*', re.I))
            
            tweet_text = tweet_text_elem.get_text(strip=True) if tweet_text_elem else ''
            
            if not tweet_text:
                return None
            
            # Skip if not English
            if not self.is_english_text(tweet_text):
                return None
            
            # Extract tweet ID from URL or data attribute
            tweet_id = None
            tweet_link = soup.find('a', href=re.compile(r'/status/\d+'))
            if tweet_link:
                href = tweet_link.get('href', '')
                match = re.search(r'/status/(\d+)', href)
                if match:
                    tweet_id = match.group(1)
            
            if not tweet_id:
                # Try to get from data-tweet-id attribute
                tweet_container = soup.find(attrs={'data-tweet-id': True})
                if tweet_container:
                    tweet_id = tweet_container.get('data-tweet-id')
            
            if not tweet_id:
                # Generate a temporary ID based on content hash
                tweet_id = str(hash(tweet_text))[:15]
            
            # Extract username
            username = 'unknown'
            user_link = soup.find('a', href=re.compile(r'^/[^/]+$'))
            if user_link:
                username = user_link.get('href', '').lstrip('/')
            else:
                # Try alternative selector
                user_elem = soup.find('span', class_=re.compile(r'.*username.*', re.I))
                if user_elem:
                    username = user_elem.get_text(strip=True).lstrip('@')
            
            # Extract engagement metrics
            like_count = 0
            retweet_count = 0
            reply_count = 0
            quote_count = 0
            
            # Try to find engagement buttons
            buttons = soup.find_all('button', {'data-testid': True})
            for button in buttons:
                testid = button.get('data-testid', '')
                text = button.get_text(strip=True)
                
                # Extract numbers from text
                numbers = re.findall(r'[\d,]+', text.replace(',', ''))
                count = int(numbers[0]) if numbers else 0
                
                if 'like' in testid.lower() or 'favorite' in testid.lower():
                    like_count = count
                elif 'retweet' in testid.lower():
                    retweet_count = count
                elif 'reply' in testid.lower():
                    reply_count = count
                elif 'quote' in testid.lower():
                    quote_count = count
            
            # Extract timestamp
            time_elem = soup.find('time')
            published_at = datetime.now().isoformat()
            if time_elem:
                datetime_attr = time_elem.get('datetime')
                if datetime_attr:
                    try:
                        published_at = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00')).isoformat()
                    except:
                        pass
            
            # Extract metadata
            hashtags = self.extract_hashtags(tweet_text)
            mentions = self.extract_mentions(tweet_text)
            urls = self.extract_urls(tweet_text)
            
            # Detect entertainment category
            category = self.detect_entertainment_category(tweet_text, hashtags)
            if not category:
                return None
            
            # Check for media
            media_type = None
            if soup.find('img', {'alt': re.compile(r'Image|Photo', re.I)}):
                media_type = 'photo'
            elif soup.find('video') or soup.find('div', class_=re.compile(r'.*video.*', re.I)):
                media_type = 'video'
            
            # Check if reply
            is_reply = soup.find('div', {'data-testid': 'reply'}) is not None
            parent_tweet_id = None
            if is_reply:
                reply_link = soup.find('a', href=re.compile(r'/status/\d+'))
                if reply_link:
                    match = re.search(r'/status/(\d+)', reply_link.get('href', ''))
                    if match:
                        parent_tweet_id = match.group(1)
            
            # Check verified badge
            user_verified = soup.find('svg', {'aria-label': 'Verified account'}) is not None
            
            return {
                'rawContent': tweet_text,
                'id': tweet_id,
                'tweetId': tweet_id,
                'date': published_at,
                'lang': 'en',
                'likeCount': like_count,
                'retweetCount': retweet_count,
                'replyCount': reply_count,
                'quoteCount': quote_count,
                'user': {
                    'username': username,
                    'id': None,  # User ID not easily available from HTML
                    'verified': user_verified,
                    'followersCount': None
                },
                'inReplyToTweetId': parent_tweet_id if is_reply else None,
                'media': [{'type': media_type}] if media_type else []
            }
            
        except Exception as e:
            logger.debug(f"Error parsing tweet element: {e}")
            return None
    
    def process_tweet(self, tweet: Dict) -> Optional[Dict]:
        """
        Process a tweet object into standardized format
        
        Args:
            tweet: Raw tweet dictionary (from HTML parsing)
            
        Returns:
            Dict with standardized fields or None if invalid
        """
        try:
            if not isinstance(tweet, dict):
                logger.debug("Tweet object is not a dict, skipping...")
                return None
            
            tweet_text = (
                tweet.get('rawContent')
                or tweet.get('renderedContent')
                or tweet.get('content')
                or ''
            )
            tweet_id = str(tweet.get('id') or tweet.get('tweetId') or '')
            
            if not tweet_id:
                logger.debug("Tweet without ID detected, skipping...")
                return None
            
            # Skip if not English
            lang = tweet.get('lang')
            if lang and lang.lower() != 'en':
                return None
            
            if not self.is_english_text(tweet_text):
                return None
            
            # Extract metadata
            hashtags = self.extract_hashtags(tweet_text)
            mentions = self.extract_mentions(tweet_text)
            urls = self.extract_urls(tweet_text)
            
            # Detect entertainment category
            category = self.detect_entertainment_category(tweet_text, hashtags)
            if not category:
                # Skip if not clearly film or music
                return None
            
            # Extract user info
            user_info = tweet.get('user') or {}
            username = user_info.get('username') or user_info.get('displayname') or 'unknown'
            user_id = str(user_info.get('id')) if user_info.get('id') else None
            
            # Extract engagement metrics
            like_count = tweet.get('likeCount', 0)
            retweet_count = tweet.get('retweetCount', 0)
            reply_count = tweet.get('replyCount', 0)
            quote_count = tweet.get('quoteCount', 0)
            
            # Check if reply
            in_reply_to = tweet.get('inReplyToTweetId')
            is_reply = in_reply_to is not None
            parent_tweet_id = str(in_reply_to) if is_reply else None
            
            # Media type
            media_type = None
            media_items = tweet.get('media') or []
            if media_items:
                if any((item.get('type') == 'photo') for item in media_items):
                    media_type = 'photo'
                elif any((item.get('type') == 'video') for item in media_items):
                    media_type = 'video'
            
            # Published date
            published_at = tweet.get('date')
            if published_at:
                try:
                    if isinstance(published_at, str):
                        published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00')).isoformat()
                    else:
                        published_at = datetime.fromisoformat(str(published_at)).isoformat()
                except ValueError:
                    published_at = str(published_at)
            else:
                published_at = datetime.now().isoformat()
            
            # Build standardized comment object
            comment = {
                'comment_id': tweet_id,
                'post_id': tweet_id,  # For tweets, post_id = comment_id
                'platform': 'Twitter',
                'author_name': username,
                'author_id': user_id,
                'comment_text': tweet_text,
                'published_at': published_at,
                'like_count': int(like_count) if like_count else 0,
                'reply_count': int(reply_count) if reply_count else 0,
                'retweet_count': int(retweet_count) if retweet_count else 0,
                'quote_count': int(quote_count) if quote_count else 0,
                'sentiment_label': None,  # To be filled by sentiment analysis
                'sentiment_score': None,  # To be filled by sentiment analysis
                'crawled_at': datetime.now().isoformat(),
                'is_reply': is_reply,
                'parent_comment_id': parent_tweet_id,
                
                # Additional fields for entertainment sentiment analysis
                'language': 'en',
                'entertainment_category': category,
                'hashtags': json.dumps(hashtags) if hashtags else None,
                'mentions': json.dumps(mentions) if mentions else None,
                'urls': json.dumps(urls) if urls else None,
                'media_type': media_type,
                'tweet_id': tweet_id,
                'user_verified': user_info.get('verified', False),
                'user_followers': user_info.get('followersCount')
            }
            
            return comment
            
        except Exception as e:
            logger.warning(f"Error processing tweet {tweet.get('id', 'unknown')}: {e}")
            return None
    
    def _scrape_tweets_from_page(self, url: str, max_results: int) -> List[Dict]:
        """
        Scrape tweets from a Twitter search/user page using Selenium
        
        Args:
            url: Twitter URL to scrape
            max_results: Maximum number of tweets to collect
            
        Returns:
            List of parsed tweet dictionaries
        """
        if not self.driver:
            self._setup_driver()
        
        tweets = []
        seen_tweet_ids = set()
        
        try:
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Wait for initial page load
            time.sleep(3)
            
            # CRITICAL: Wait for React to render tweets (Twitter uses dynamic rendering)
            logger.debug("Waiting for tweets to render...")
            
            # Try to wait for tweet elements to appear (with timeout)
            tweet_loaded = False
            wait_attempts = 0
            max_wait_attempts = 10  # 10 attempts x 2 seconds = 20 seconds max
            
            while not tweet_loaded and wait_attempts < max_wait_attempts:
                try:
                    # Try to find at least one tweet element
                    WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'article[data-testid="tweet"]'))
                    )
                    tweet_loaded = True
                    logger.debug(f"✅ Tweets loaded after {wait_attempts * 2 + 2} seconds")
                except TimeoutException:
                    wait_attempts += 1
                    if wait_attempts < max_wait_attempts:
                        logger.debug(f"Tweets not yet loaded, waiting... (attempt {wait_attempts}/{max_wait_attempts})")
                        # Scroll a bit to trigger loading
                        self.driver.execute_script("window.scrollBy(0, 100);")
                        time.sleep(1)
            
            if not tweet_loaded:
                logger.warning("⚠️ Tweets did not load within timeout - may not find any tweets")
            
            # Additional wait for complete rendering
            time.sleep(2)
            
            # Save debug info after page load
            self._save_debug_info("01_page_loaded")
            
            # Check if login is required
            page_source = self.driver.page_source.lower()
            current_url = self.driver.current_url.lower()
            
            # More thorough login check
            login_indicators = ['sign in', 'log in', 'login', 'create account']
            if any(keyword in page_source for keyword in login_indicators):
                # Check if we're actually on a login page or just seeing login button
                if 'i/flow/login' in current_url or 'login' in current_url:
                    logger.error("❌ COOKIES INVALID: Redirected to login page")
                    logger.error("   Your cookies may have expired or are invalid")
                    logger.error("   Please login again using option 6")
                    return []  # Return empty list instead of trying to crawl
                else:
                    # Just a login button visible, but may still be able to browse
                    logger.debug("Login button visible but not on login page - continuing...")
            else:
                logger.debug("✅ No login required - cookies are valid")
            
            # Try multiple selectors (Twitter may have changed structure)
            selectors = [
                'article[data-testid="tweet"]',  # Primary selector
                'article[role="article"]',       # Alternative
                'div[data-testid="tweet"]',      # Alternative
            ]
            
            # Scroll and collect tweets
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 50
            no_tweets_count = 0  # Track consecutive scrolls with no tweets
            
            while len(tweets) < max_results and scroll_attempts < max_scroll_attempts:
                # Try each selector until we find tweets
                tweet_elements = []
                for selector in selectors:
                    tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if tweet_elements:
                        logger.debug(f"Found {len(tweet_elements)} elements with selector: {selector}")
                        break
                
                if not tweet_elements:
                    no_tweets_count += 1
                    logger.debug(f"No tweet elements found (attempt {no_tweets_count})")
                    
                    # Save debug info on first failure to find tweets
                    if no_tweets_count == 1:
                        self._save_debug_info("02_no_tweets_found")
                        logger.warning("🐛 Debug: Trying to find tweets but none found yet")
                        logger.warning("   Check debug_output/ folder for screenshots and HTML")
                    
                    # If we've scrolled multiple times with no tweets, likely login required or page empty
                    if no_tweets_count >= 3:
                        self._save_debug_info("03_no_tweets_after_scrolls")
                        logger.warning("No tweets found after multiple scrolls. Possible reasons:")
                        logger.warning("  1. Twitter requires login to view search results")
                        logger.warning("  2. Page structure has changed")
                        logger.warning("  3. Rate limited or blocked")
                        logger.warning("  4. Cookies expired or invalid")
                        logger.warning("")
                        logger.warning("🐛 Debug files saved to debug_output/ - check screenshots and HTML")
                        break
                else:
                    no_tweets_count = 0  # Reset counter if we found tweets
                
                for tweet_elem in tweet_elements:
                    if len(tweets) >= max_results:
                        break
                    
                    try:
                        parsed_tweet = self._parse_tweet_element(tweet_elem)
                        if parsed_tweet and parsed_tweet.get('id'):
                            tweet_id = parsed_tweet['id']
                            if tweet_id not in seen_tweet_ids:
                                seen_tweet_ids.add(tweet_id)
                                tweets.append(parsed_tweet)
                    except Exception as e:
                        logger.debug(f"Error parsing tweet element: {e}")
                        continue
                
                # Scroll down to load more tweets
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)  # Increased wait time for dynamic content
                
                # Check if we've reached the bottom
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                    if scroll_attempts >= 3:
                        logger.info("Reached end of page or no more tweets loading")
                        break
                else:
                    scroll_attempts = 0
                    last_height = new_height
                
                self._smart_delay(len(tweets))
            
            logger.info(f"Collected {len(tweets)} tweets from page")
            
            if len(tweets) == 0:
                logger.warning("⚠️ No tweets collected. This may indicate:")
                logger.warning("  - Twitter requires login (most common)")
                logger.warning("  - Page structure has changed")
                logger.warning("  - Rate limiting or blocking")
                logger.warning("  - Try running with headless=False to see what's happening")
            
        except Exception as e:
            logger.error(f"Error scraping page {url}: {e}")
            raise
        
        return tweets
    
    def _build_search_url(self, query: str, since: Optional[str] = None, 
                         until: Optional[str] = None) -> str:
        """
        Build Twitter search URL
        
        Args:
            query: Search query
            since: Start date (YYYY-MM-DD)
            until: End date (YYYY-MM-DD)
            
        Returns:
            Twitter search URL
        """
        base_url = "https://twitter.com/search"
        
        # Use sort_by: 'top' for high engagement tweets, 'latest' for newest tweets
        sort_param = 'top' if self.sort_by == 'top' else 'live'
        
        params = {
            'q': query,
            'src': 'typed_query',
            'f': sort_param  # 'top' = popular tweets, 'live' = latest tweets
        }
        
        if since:
            params['since'] = since
        if until:
            params['until'] = until
        
        query_string = '&'.join([f"{k}={quote_plus(str(v))}" for k, v in params.items()])
        return f"{base_url}?{query_string}"
    
    def scrape_by_keywords(self, keywords: List[str], max_tweets: int = 1000,
                          since: Optional[str] = None, until: Optional[str] = None,
                          category: Optional[str] = None) -> List[Dict]:
        """
        Scrape tweets by keywords
        
        Args:
            keywords: List of keywords/hashtags to search
            max_tweets: Maximum number of tweets to scrape
            since: Start date (YYYY-MM-DD)
            until: End date (YYYY-MM-DD)
            category: Filter by category ('film' or 'music')
            
        Returns:
            List of processed tweet dictionaries
        """
        logger.info(f"Scraping tweets with keywords: {keywords}")
        logger.info(f"Max tweets: {max_tweets}, Category: {category or 'any'}")
        
        all_tweets = []
        
        for keyword in keywords:
            logger.info(f"Processing keyword: {keyword}")
            
            # Build query
            query = f"{keyword} lang:en"  # Only English
            
            if since:
                query += f" since:{since}"
            if until:
                query += f" until:{until}"
            
            logger.info(f"Query: {query}")
            
            count = 0
            skipped_non_english = 0
            skipped_wrong_category = 0
            
            try:
                # Build search URL
                search_url = self._build_search_url(query, since, until)
                
                # Scrape tweets from page
                raw_tweets = self._scrape_tweets_from_page(search_url, max_tweets)
                
                for raw_tweet in raw_tweets:
                    if count >= max_tweets:
                        break
                    
                    processed = self.process_tweet(raw_tweet)
                    
                    if not processed:
                        skipped_non_english += 1
                        continue
                    
                    if category and processed.get('entertainment_category') != category:
                        skipped_wrong_category += 1
                        continue
                    
                    all_tweets.append(processed)
                    count += 1
                    
                    if count % 100 == 0:
                        logger.info(f"Collected {count} tweets (keyword: {keyword})")
                    
                    self._smart_delay(count)
                
                logger.info(f"Keyword '{keyword}': Collected {count} tweets")
                logger.info(f"  Skipped (non-English): {skipped_non_english}")
                logger.info(f"  Skipped (wrong category): {skipped_wrong_category}")
            
            except RuntimeError as e:
                logger.error(f"Error scraping keyword '{keyword}': {e}")
                continue
        
        logger.info(f"Total collected: {len(all_tweets)} tweets")
        return all_tweets
    
    def scrape_by_user(self, username: str, max_tweets: int = 500,
                      since: Optional[str] = None, until: Optional[str] = None,
                      category: Optional[str] = None) -> List[Dict]:
        """
        Scrape tweets from a specific user
        
        Args:
            username: Twitter username (without @)
            max_tweets: Maximum number of tweets
            since: Start date (YYYY-MM-DD)
            until: End date (YYYY-MM-DD)
            category: Filter by category ('film' or 'music')
            
        Returns:
            List of processed tweet dictionaries
        """
        logger.info(f"Scraping tweets from user: @{username}")
        
        # Build query
        query = f"from:{username} lang:en"
        
        if since:
            query += f" since:{since}"
        if until:
            query += f" until:{until}"
        
        logger.info(f"Query: {query}")
        
        tweets = []
        skipped_non_english = 0
        skipped_wrong_category = 0
        
        try:
            # Build user profile URL
            user_url = f"https://twitter.com/{username}"
            
            # Scrape tweets from user profile
            raw_tweets = self._scrape_tweets_from_page(user_url, max_tweets)
            
            for raw_tweet in raw_tweets:
                if len(tweets) >= max_tweets:
                    break
                
                processed = self.process_tweet(raw_tweet)
                
                if not processed:
                    skipped_non_english += 1
                    continue
                
                if category and processed.get('entertainment_category') != category:
                    skipped_wrong_category += 1
                    continue
                
                tweets.append(processed)
                
                if len(tweets) % 50 == 0:
                    logger.info(f"Collected {len(tweets)} tweets from @{username}")
                
                self._smart_delay(len(tweets))
            
            logger.info(f"Collected {len(tweets)} tweets from @{username}")
            logger.info(f"  Skipped (non-English): {skipped_non_english}")
            logger.info(f"  Skipped (wrong category): {skipped_wrong_category}")
            
        except RuntimeError as e:
            logger.error(f"Error scraping user @{username}: {e}")
        
        return tweets
    
    def scrape_film_tweets(self, max_tweets: int = 1000,
                          since: Optional[str] = None, until: Optional[str] = None) -> List[Dict]:
        """Scrape tweets about films"""
        return self.scrape_by_keywords(
            self.FILM_KEYWORDS,
            max_tweets=max_tweets,
            since=since,
            until=until,
            category='film'
        )
    
    def scrape_music_tweets(self, max_tweets: int = 1000,
                           since: Optional[str] = None, until: Optional[str] = None) -> List[Dict]:
        """Scrape tweets about music"""
        return self.scrape_by_keywords(
            self.MUSIC_KEYWORDS,
            max_tweets=max_tweets,
            since=since,
            until=until,
            category='music'
        )
    
    def scrape_all_entertainment(self, max_tweets: int = 2000,
                                since: Optional[str] = None, until: Optional[str] = None) -> Dict:
        """
        Scrape both film and music tweets
        
        Returns:
            Dict with 'film' and 'music' keys
        """
        logger.info("Scraping all entertainment tweets...")
        
        film_tweets = self.scrape_film_tweets(
            max_tweets=max_tweets // 2,
            since=since,
            until=until
        )
        
        music_tweets = self.scrape_music_tweets(
            max_tweets=max_tweets // 2,
            since=since,
            until=until
        )
        
        return {
            'film': film_tweets,
            'music': music_tweets,
            'total': len(film_tweets) + len(music_tweets)
        }
    
    def clean_and_save(self, tweets: List[Dict], filename: str = None,
                      clean_data: bool = True, save_format: str = 'both') -> Dict:
        """
        Clean data and save to file
        
        Args:
            tweets: List of tweet dictionaries
            filename: Output filename (without extension)
            clean_data: Whether to clean data
            save_format: 'csv', 'json', or 'both'
            
        Returns:
            Dict with file paths
        """
        if not tweets:
            logger.warning("No tweets to save")
            return {}
        
        # Create output directory
        output_dir = Path(f'data/{self.output_folder}')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"entertainment_tweets_{timestamp}"
        
        saved_files = {}
        
        # Clean data if requested
        if clean_data:
            logger.info(f"Cleaning {len(tweets)} tweets...")
            df = pd.DataFrame(tweets)
            cleaned_df = self.cleaner.clean_dataframe(df)
            tweets_df = cleaned_df
        else:
            tweets_df = pd.DataFrame(tweets)
        
        # Save CSV
        if save_format in ('csv', 'both'):
            csv_file = output_dir / f"{filename}.csv"
            tweets_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            saved_files['csv'] = str(csv_file)
            logger.info(f"Saved CSV: {csv_file}")
        
        # Save JSON
        if save_format in ('json', 'both'):
            json_file = output_dir / f"{filename}.json"
            tweets_dict = tweets_df.to_dict('records')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(tweets_dict, f, indent=2, ensure_ascii=False, default=str)
            saved_files['json'] = str(json_file)
            logger.info(f"Saved JSON: {json_file}")
        
        return saved_files
    
    def get_stats(self, tweets: List[Dict]) -> Dict:
        """Get statistics about collected tweets"""
        if not tweets:
            return {}
        
        df = pd.DataFrame(tweets)
        
        stats = {
            'total_tweets': len(tweets),
            'film_tweets': len(df[df.get('entertainment_category') == 'film']) if 'entertainment_category' in df.columns else 0,
            'music_tweets': len(df[df.get('entertainment_category') == 'music']) if 'entertainment_category' in df.columns else 0,
            'total_likes': int(df['like_count'].sum()) if 'like_count' in df.columns else 0,
            'total_retweets': int(df['retweet_count'].sum()) if 'retweet_count' in df.columns else 0,
            'total_replies': int(df['reply_count'].sum()) if 'reply_count' in df.columns else 0,
            'avg_likes': float(df['like_count'].mean()) if 'like_count' in df.columns else 0,
            'avg_retweets': float(df['retweet_count'].mean()) if 'retweet_count' in df.columns else 0,
            'tweets_with_media': len(df[df.get('media_type').notna()]) if 'media_type' in df.columns else 0,
            'verified_users': len(df[df.get('user_verified') == True]) if 'user_verified' in df.columns else 0,
        }
        
        # Date range
        if 'published_at' in df.columns:
            dates = pd.to_datetime(df['published_at'], errors='coerce')
            stats['date_range'] = {
                'earliest': dates.min().isoformat() if not dates.empty else None,
                'latest': dates.max().isoformat() if not dates.empty else None
            }
        
        return stats
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup driver"""
        self._close_driver()


def interactive_mode():
    """Interactive menu for crawler"""
    print("\n" + "="*70)
    print("🐦 TWITTER ENTERTAINMENT CRAWLER")
    print("="*70)
    print("\n⚠️ LƯU Ý QUAN TRỌNG:")
    print("   1. Mỗi lần chạy cần LOGIN lại (option 6)")
    print("   2. Cookies chỉ tồn tại trong phiên làm việc này")
    print("   3. Sau khi login xong, có thể scrape nhiều lần trong cùng phiên")
    print("   4. Đóng terminal = mất cookies, phải login lại lần sau")
    
    # Ask user which browser to use
    print("\n🌐 CHỌN BROWSER:")
    print("   1. Chrome (default - có thể bị Twitter phát hiện)")
    print("   2. Firefox (ít bị phát hiện hơn)")
    print("   3. Undetected ChromeDriver (tốt nhất - cần cài: pip install undetected-chromedriver)")
    
    browser_choice = input("\nChọn browser (1/2/3, default=1): ").strip() or "1"
    
    use_firefox = (browser_choice == "2")
    use_undetected = (browser_choice == "3")
    
    if use_undetected:
        try:
            import undetected_chromedriver
        except ImportError:
            print("\n⚠️ undetected-chromedriver chưa được cài đặt!")
            print("   Cài đặt: pip install undetected-chromedriver")
            print("   Fallback về Chrome thường...")
            use_undetected = False
    
    # Ask user for output folder
    print("\n📁 CHỌN THƯ MỤC LƯU DỮ LIỆU:")
    print("   Dữ liệu sẽ được lưu trong: data/{folder_name}/")
    default_folder = "twitter_entertainment"
    output_folder = input(f"   Tên folder (default: {default_folder}): ").strip() or default_folder
    # Sanitize folder name (remove invalid characters)
    output_folder = "".join(c for c in output_folder if c.isalnum() or c in ('_', '-')).strip()
    if not output_folder:
        output_folder = default_folder
    
    print(f"   ✅ Dữ liệu sẽ được lưu vào: data/{output_folder}/")
    
    # Ask user for sort preference
    print("\n🔥 CHỌN CÁCH SẮP XẾP TWEETS:")
    print("   1. Latest (mới nhất - có thể tương tác thấp)")
    print("   2. Top (phổ biến nhất - tương tác cao, trending)")
    sort_choice = input("\nChọn (1/2, default=2): ").strip() or "2"
    sort_by = "top" if sort_choice == "2" else "latest"
    print(f"   ✅ Sẽ crawl tweets: {'TOP/Popular (tương tác cao)' if sort_by == 'top' else 'Latest (mới nhất)'}")
    
    # Ask user for debug mode
    print("\n🐛 BẬT DEBUG MODE?")
    print("   Debug mode sẽ lưu screenshots và HTML để troubleshoot")
    print("   Hữu ích khi gặp lỗi không crawl được data")
    debug_input = input("   Bật debug mode? (y/n, default=n): ").strip().lower()
    debug_mode = (debug_input == 'y')
    if debug_mode:
        print("   ✅ Debug mode BẬT - screenshots/HTML sẽ được lưu vào debug_output/")
    
    # Use context manager to ensure driver cleanup
    crawler = TwitterEntertainmentCrawler(
        headless=False,  # Set to False for better login experience
        use_firefox=use_firefox,
        use_undetected=use_undetected,
        output_folder=output_folder,
        debug_mode=debug_mode,
        sort_by=sort_by
    )
    
    try:
        while True:
            print("\n📚 CHỌN CHỨC NĂNG:")
            print("   1. Scrape Film Tweets")
            print("   2. Scrape Music Tweets")
            print("   3. Scrape All Entertainment (Film + Music)")
            print("   4. Scrape by Keywords (Custom)")
            print("   5. Scrape by User")
            print("   6. Login to Twitter/X (Manual - tự điền trên browser)")
            print("   0. Exit")
            
            choice = input("\nNhập lựa chọn (0-6): ").strip()
            
            if choice == "6":
                print("\n🔐 MANUAL LOGIN")
                print("="*70)
                print("Browser sẽ mở, vui lòng tự điền username/password trên Twitter/X")
                print("Sau khi login thành công, cookies sẽ được lưu vào memory")
                print("="*70)
                
                input("\n⏸️  Nhấn Enter để mở browser và bắt đầu login...")
                
                if crawler.manual_login(timeout=300):
                    print("\n✅ Login thành công!")
                    print("   💾 Cookies đã được lưu vào session memory")
                    print("   Đang đóng browser login...")
                    
                    # Close browser after successful login
                    crawler._close_driver()
                    
                    print("   ✅ Browser login đã đóng.")
                    print("\n🎯 Bạn có thể scrape tweets ngay bây giờ!")
                    print("   Crawler sẽ tự động sử dụng cookies đã lưu trong phiên này.")
                    print("   ⚠️  Cookies chỉ tồn tại trong phiên này (không lưu ra file)")
                else:
                    print("\n❌ Login không thành công hoặc timeout.")
                    print("   Có thể do:")
                    print("   - Chưa hoàn thành login trong thời gian cho phép")
                    print("   - Có lỗi trong quá trình login")
                    print("   Vui lòng thử lại (option 6)")
                    
                    # Close browser if login failed
                    crawler._close_driver()
                continue
            
            if choice == "0":
                print("\n👋 Goodbye!")
                break
            
            if choice == "6":
                continue  # Already handled above
            
            try:
                max_tweets = int(input("\nSố lượng tweets tối đa (default 500): ").strip() or "500")
                
                # Date range (optional)
                use_date_range = input("Sử dụng date range? (y/n, default=n): ").strip().lower() == 'y'
                since = None
                until = None
                if use_date_range:
                    since = input("Start date (YYYY-MM-DD, or press Enter for last 7 days): ").strip()
                    until = input("End date (YYYY-MM-DD, or press Enter for today): ").strip()
                    
                    if not since:
                        since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                    if not until:
                        until = datetime.now().strftime("%Y-%m-%d")
                
                clean_data = input("Clean data? (y/n, default=y): ").strip().lower() != 'n'
                
                tweets = []
                
                if choice == "1":
                    print(f"\n🔍 Scraping film tweets (max: {max_tweets})...")
                    tweets = crawler.scrape_film_tweets(
                        max_tweets=max_tweets,
                        since=since,
                        until=until
                    )
                
                elif choice == "2":
                    print(f"\n🔍 Scraping music tweets (max: {max_tweets})...")
                    tweets = crawler.scrape_music_tweets(
                        max_tweets=max_tweets,
                        since=since,
                        until=until
                    )
                
                elif choice == "3":
                    print(f"\n🔍 Scraping all entertainment tweets (max: {max_tweets})...")
                    result = crawler.scrape_all_entertainment(
                        max_tweets=max_tweets,
                        since=since,
                        until=until
                    )
                    tweets = result['film'] + result['music']
                    print(f"\n✅ Collected: {result['total']} tweets")
                    print(f"   Film: {len(result['film'])}")
                    print(f"   Music: {len(result['music'])}")
                
                elif choice == "4":
                    keywords_input = input("\nNhập keywords (cách nhau bằng dấu phẩy): ").strip()
                    keywords = [k.strip() for k in keywords_input.split(',')]
                    category = input("Category filter (film/music/none, default=none): ").strip().lower() or None
                    
                    print(f"\n🔍 Scraping tweets with keywords: {keywords}...")
                    tweets = crawler.scrape_by_keywords(
                        keywords=keywords,
                        max_tweets=max_tweets,
                        since=since,
                        until=until,
                        category=category if category != 'none' else None
                    )
                
                elif choice == "5":
                    username = input("\nNhập username (không cần @): ").strip().lstrip('@')
                    category = input("Category filter (film/music/none, default=none): ").strip().lower() or None
                    
                    print(f"\n🔍 Scraping tweets from @{username}...")
                    tweets = crawler.scrape_by_user(
                        username=username,
                        max_tweets=max_tweets,
                        since=since,
                        until=until,
                        category=category if category != 'none' else None
                    )
                
                else:
                    print("\n❌ Lựa chọn không hợp lệ!")
                    continue
                
                # Show stats
                if tweets:
                    stats = crawler.get_stats(tweets)
                    print(f"\n📊 STATISTICS:")
                    print(f"   Total tweets: {stats['total_tweets']}")
                    print(f"   Film tweets: {stats['film_tweets']}")
                    print(f"   Music tweets: {stats['music_tweets']}")
                    print(f"   Total likes: {stats['total_likes']:,}")
                    print(f"   Avg likes: {stats['avg_likes']:.1f}")
                    
                    # Save data
                    save = input("\n💾 Lưu dữ liệu? (y/n, default=y): ").strip().lower() != 'n'
                    if save:
                        save_format = input("Format (csv/json/both, default=both): ").strip().lower() or "both"
                        saved_files = crawler.clean_and_save(
                            tweets,
                            clean_data=clean_data,
                            save_format=save_format
                        )
                        
                        if saved_files:
                            print(f"\n✅ Saved files:")
                            for fmt, path in saved_files.items():
                                print(f"   {fmt.upper()}: {path}")
                else:
                    print("\n❌ Không có tweets nào được thu thập!")
            
            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupted by user!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                logger.error(f"Error in interactive mode: {e}", exc_info=True)
    finally:
        crawler._close_driver()


def main():
    """Main function"""
    print("\n" + "="*70)
    print("🐦 TWITTER ENTERTAINMENT CRAWLER - Using Selenium/BeautifulSoup")
    print("="*70)
    print("\nTÍNH NĂNG:")
    print("  ✅ Scrape tweets về films và music")
    print("  ✅ Lọc chỉ English tweets")
    print("  ✅ Hỗ trợ nhiều search modes")
    print("  ✅ Filter by date range")
    print("  ✅ Export CSV/JSON")
    print("  ✅ Tích hợp data cleaning")
    
    print("\n⚠️ LƯU Ý QUAN TRỌNG:")
    print("  - Chỉ scrape English tweets")
    print("  - Tự động filter entertainment content (film/music)")
    print("  - Tuân thủ Twitter Terms of Service")
    print("  - Cần cài đặt Chrome/Chromium và ChromeDriver")
    print("\n🚨 TRÁNH BỊ BLOCK:")
    print("  - Delay tự động: 1-5 giây giữa mỗi request")
    print("  - Batch delay: 5-8 giây sau mỗi 50 tweets")
    print("  - Khuyến nghị: max_tweets <= 500 mỗi lần")
    print("  - Nghỉ 30 phút - 1 giờ giữa các lần scrape")
    print("  - Sử dụng headless mode để tránh detection")
    print("  - Xem chi tiết: TWITTER_CRAWLER_SAFETY.md")
    
    interactive_mode()


if __name__ == "__main__":
    main()

