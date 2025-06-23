from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import time
from datetime import datetime, timedelta
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
import logging
import os

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking.log'),
        logging.StreamHandler()
    ]
)

# Constants for configuration
ACCOUNT_NUMBER = os.environ.get('ACCOUNT', '1')
USERNAME = os.environ.get('TENNIS_USERNAME2') if ACCOUNT_NUMBER == '2' else os.environ.get('TENNIS_USERNAME')
PASSWORD = os.environ.get('TENNIS_PASSWORD')
CARD_NUMBER = os.environ.get('CARD_NUMBER')
CARD_EXPIRY = os.environ.get('CARD_EXPIRY')
CARD_CVC = os.environ.get('CARD_CVC')
CHROME_DRIVER_PATH = ChromeDriverManager().install()
DATE = os.environ.get('BOOKING_DATE')
BOOKING_START_HOUR = int(os.environ.get('BOOKING_HOUR'))
BOOKING_START_MINUTE = int(os.environ.get('BOOKING_MINUTES'))
COURT = os.environ.get('BOOKING_COURT')

# Check if username and password are available
if not USERNAME or not PASSWORD:
    logging.error("Username or password not defined!")
    exit(1)

# Log account information
logging.info(f"🔑 Using account {'secondary' if ACCOUNT_NUMBER == '2' else 'primary'} (TENNIS_USERNAME{'2' if ACCOUNT_NUMBER == '2' else ''})")

# Calculate total minutes and format display
TOTAL_MINUTES = (BOOKING_START_HOUR * 60) + BOOKING_START_MINUTE
HOUR_STR = f"{BOOKING_START_HOUR:02d}:{BOOKING_START_MINUTE:02d}"
logging.info(f"Booking for {DATE} at {HOUR_STR}")
logging.info(f"System minutes: {TOTAL_MINUTES}")

resource_ids = {
    'Court1': 'ad7d3c7b-9dff-4442-bb18-4761970f11c0',
    'Court2': 'f942cbed-3f8a-4828-9afc-2c0a23886ffa',
    'Court3': '7626935c-1e38-49ca-a3ff-52205ed98a81',
    'Court4': '1d7ac83f-5fdb-4fe4-a743-5383b7a1641f'
}

start_time = TOTAL_MINUTES
court = COURT
booking_date = datetime.strptime(DATE, '%Y-%m-%d')

# Chrome configuration with improved settings
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.page_load_strategy = 'eager'
# Add user agent to appear more like a real browser
options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Sample URL template
SAMPLE_URL = 'https://clubspark.lta.org.uk/SouthwarkPark/Booking/Book?Contacts%5B0%5D.IsPrimary=true&Contacts%5B0%5D.IsJunior=false&Contacts%5B0%5D.IsPlayer=true&ResourceID=ad7d3c7b-9dff-4442-bb18-4761970f11c0&Date=2025-06-28&SessionID=c3791901-4d64-48f5-949d-85d01c4633b9&StartTime=1140&EndTime=1200&Category=0&SubCategory=0&VenueID=4123ed12-8dd6-4f48-a706-6ab2fbde16ba&ResourceGroupID=4123ed12-8dd6-4f48-a706-6ab2fbde16ba'

def timer(target_time_str):
    """Wait until a specific time of day."""
    target_time = datetime.strptime(target_time_str, "%H:%M").replace(
        year=datetime.now().year,
        month=datetime.now().month,
        day=datetime.now().day
    )
    now = datetime.now()
    wait_seconds = (target_time - now).total_seconds()
    if wait_seconds > 0:
        logging.info(f"Waiting {wait_seconds:.0f} seconds until {target_time_str}")
        time.sleep(wait_seconds)

def handle_cookie_consent(driver, wait):
    """Handle cookie consent banners that might appear."""
    cookie_selectors = [
        'button.osano-cm-dialog__close.osano-cm-close',
        'button.osano-cm-deny',
        'button.osano-cm-accept-all',
        'button[aria-label="Close"]',
        'button[title="Close"]'
    ]
    
    for selector in cookie_selectors:
        try:
            cookie_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)), timeout=3)
            cookie_button.click()
            logging.info(f"Clicked cookie consent button: {selector}")
            time.sleep(1)  # Give time for the banner to disappear
            return True
        except (TimeoutException, NoSuchElementException):
            continue
    
    # Try to click anywhere on the page to dismiss overlays
    try:
        driver.execute_script("document.body.click();")
        time.sleep(0.5)
    except:
        pass
    
    return False

def safe_click(driver, wait, element_xpath, max_retries=3):
    """Safely click an element with retry logic."""
    for attempt in range(max_retries):
        try:
            element = wait.until(EC.element_to_be_clickable((By.XPATH, element_xpath)))
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            
            # Try JavaScript click first
            driver.execute_script("arguments[0].click();", element)
            return True
            
        except ElementClickInterceptedException:
            logging.warning(f"Click intercepted on attempt {attempt + 1}, handling overlays...")
            handle_cookie_consent(driver, wait)
            
            # Try regular click as fallback
            try:
                element = driver.find_element(By.XPATH, element_xpath)
                element.click()
                return True
            except:
                pass
                
        except Exception as e:
            logging.error(f"Error clicking element on attempt {attempt + 1}: {e}")
    
    return False

def enter_data(driver, wait, element_xpath, input_text, use_js=False):
    """Enter data into a field with improved error handling."""
    try:
        element = wait.until(EC.presence_of_element_located((By.XPATH, element_xpath)))
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.5)
        
        if use_js:
            # Use JavaScript to set value directly
            driver.execute_script(f"arguments[0].value = '{input_text}';", element)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", element)
        else:
            element.clear()
            element.send_keys(input_text)
            element.send_keys(Keys.RETURN)
            
        return True
        
    except Exception as e:
        logging.error(f"Error entering data: {e}")
        return False

def enter_iframe_data(driver, wait, iframe_xpath, input_text):
    """Enter data into an iframe field (for Stripe payment)."""
    try:
        # Switch to iframe
        iframe = wait.until(EC.presence_of_element_located((By.XPATH, iframe_xpath)))
        driver.switch_to.frame(iframe)
        
        # Find input field inside iframe
        input_field = wait.until(EC.presence_of_element_located((By.TAG_NAME, "input")))
        input_field.clear()
        input_field.send_keys(input_text)
        
        # Switch back to main content
        driver.switch_to.default_content()
        return True
        
    except Exception as e:
        logging.error(f"Error entering iframe data: {e}")
        driver.switch_to.default_content()
        return False

def initialize(driver, wait):
    """Initialize the webdriver, navigate to the login page, and log in."""
    try:
        # Navigate to login page
        driver.get("https://clubspark.lta.org.uk/SouthwarkPark/Account/SignIn?returnUrl=https%3a%2f%2fclubspark.lta.org.uk%2fSouthwarkPark%2fBooking%2fBookByDate")
        time.sleep(2)
        
        # Handle cookie consent if it appears
        handle_cookie_consent(driver, wait)
        
        # Click on login button
        login_button_xpath = '/html/body/div[3]/div[1]/div[2]/div[1]/div[2]/form/button'
        if not safe_click(driver, wait, login_button_xpath):
            # Try alternative selector
            safe_click(driver, wait, '//button[contains(text(), "Sign in") or contains(text(), "Log in")]')
        
        time.sleep(2)
        
        # Enter username - note the ID might be dynamic
        username_entered = False
        username_selectors = [
            '//*[@id="154:0"]',
            '//input[@type="email"]',
            '//input[@name="username"]',
            '//input[contains(@placeholder, "Email")]'
        ]
        
        for selector in username_selectors:
            if enter_data(driver, wait, selector, USERNAME):
                username_entered = True
                break
        
        if not username_entered:
            logging.error("Failed to enter username")
            return False
            
        # Enter password
        password_selectors = [
            '//*[@id="input-2"]',
            '//input[@type="password"]',
            '//input[@name="password"]',
            '//input[contains(@placeholder, "Password")]'
        ]
        
        for selector in password_selectors:
            if enter_data(driver, wait, selector, PASSWORD):
                break
        
        # Wait for login to complete
        time.sleep(3)
        
        # Handle any post-login popups
        handle_cookie_consent(driver, wait)
        
        logging.info("Login successful")
        return True
        
    except Exception as e:
        logging.error(f"Error during initialization: {e}")
        # Take screenshot for debugging
        try:
            driver.save_screenshot("login_error.png")
        except:
            pass
        return False

def main():
    driver = None
    try:
        # Build booking URL
        parsed = urlparse(SAMPLE_URL)
        query = parse_qs(parsed.query)
        query["Date"] = [booking_date.strftime('%Y-%m-%d')]
        query["StartTime"] = [str(start_time)]
        query["EndTime"] = [str(start_time + 60)]
        query["ResourceID"] = [resource_ids[court]]
        new_query = urlencode(query, doseq=True)
        booking_url = urlunparse(parsed._replace(query=new_query))
        
        logging.info(f"Booking URL: {booking_url}")
        
        # Initialize WebDriver
        driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=options)
        wait = WebDriverWait(driver, 15)  # Increased timeout
        
        # Login
        if not initialize(driver, wait):
            logging.error("Failed to login")
            return
        
        # Navigate to booking page
        driver.get(booking_url)
        time.sleep(2)
        
        # Click pay now button
        if not safe_click(driver, wait, '//*[@id="paynow"]'):
            logging.error("Failed to click pay now button")
            return
        
        time.sleep(2)
        
        # Payment process with Stripe
        logging.info("Entering payment details...")
        
        # Card number
        if not enter_iframe_data(driver, wait, '//*[@id="cs-stripe-elements-card-number"]/div/iframe', CARD_NUMBER):
            logging.error("Failed to enter card number")
        
        # Card expiry
        if not enter_iframe_data(driver, wait, '//*[@id="cs-stripe-elements-card-expiry"]/div/iframe', CARD_EXPIRY):
            logging.error("Failed to enter card expiry")
        
        # Card CVC
        if not enter_iframe_data(driver, wait, '//*[@id="cs-stripe-elements-card-cvc"]/div/iframe', CARD_CVC):
            logging.error("Failed to enter card CVC")
        
        # Submit payment
        if safe_click(driver, wait, '//*[@id="cs-stripe-elements-submit-button"]'):
            logging.info("Payment submitted successfully")
        else:
            logging.error("Failed to submit payment")
        
        # Wait for confirmation
        time.sleep(5)
        
        # Take screenshot of final page
        driver.save_screenshot("booking_complete.png")
        
    except Exception as e:
        logging.error(f"An error occurred in the main flow: {e}")
        if driver:
            driver.save_screenshot("error_screenshot.png")
    finally:
        if driver:
            time.sleep(5)
            driver.quit()
        logging.info("Done!")

if __name__ == "__main__":
    main()
