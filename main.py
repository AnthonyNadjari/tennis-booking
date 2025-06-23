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
from selenium.common.exceptions import NoSuchElementException, TimeoutException
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

# Check if we're running in CI/CD
IS_CI = os.environ.get('CI', 'false').lower() == 'true'

# Check if username and password are available
if not USERNAME or not PASSWORD:
    logging.error("Username or password not defined!")
    exit(1)

# Log account information
logging.info(f"🔑 Utilisation du compte {'secondaire' if ACCOUNT_NUMBER == '2' else 'principal'} (TENNIS_USERNAME{'2' if ACCOUNT_NUMBER == '2' else ''})")
logging.info(f"Running in {'CI/CD' if IS_CI else 'local'} environment")

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

# Configuration Chrome - only use headless in CI
options = webdriver.ChromeOptions()
if IS_CI:
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")  # Important for headless
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

# Always use these options
options.page_load_strategy = 'normal'  # Changed from 'eager' to ensure full page load

def timer(target_time_str):
    """
    Wait until a specific time of day.
    """
    target_time = datetime.strptime(target_time_str, "%H:%M").replace(
        year=datetime.now().year,
        month=datetime.now().month,
        day=datetime.now().day
    )
    now = datetime.now()
    wait_seconds = (target_time - now).total_seconds()
    if wait_seconds > 0:
        time.sleep(wait_seconds)

def handle_cookie_consent():
    """
    Handle cookie consent banner - try multiple methods
    """
    try:
        # Method 1: Close button
        close_button = driver.find_element(By.CSS_SELECTOR, 'button.osano-cm-dialog__close')
        close_button.click()
        logging.info("Closed cookie banner via close button")
        time.sleep(1)
        return True
    except:
        pass
    
    try:
        # Method 2: Deny button
        deny_button = driver.find_element(By.CSS_SELECTOR, 'button.osano-cm-deny')
        deny_button.click()
        logging.info("Closed cookie banner via deny button")
        time.sleep(1)
        return True
    except:
        pass
    
    try:
        # Method 3: Accept all (sometimes it's the only option)
        accept_button = driver.find_element(By.CSS_SELECTOR, 'button.osano-cm-accept-all')
        accept_button.click()
        logging.info("Accepted cookies")
        time.sleep(1)
        return True
    except:
        pass
    
    # If headless, try JavaScript click
    if IS_CI:
        try:
            driver.execute_script("""
                var buttons = document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    if (buttons[i].textContent.includes('Deny') || 
                        buttons[i].textContent.includes('Close') ||
                        buttons[i].className.includes('osano')) {
                        buttons[i].click();
                        break;
                    }
                }
            """)
            time.sleep(1)
            logging.info("Handled cookie banner via JavaScript")
            return True
        except:
            pass
    
    return False

def enter_data(element_xpath, input_text):
    """
    Enter data into a field specified by an XPath and send a return key.
    """
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, element_xpath)))
        element = driver.find_element(By.XPATH, element_xpath)
        element.clear()
        element.send_keys(input_text)
        element.send_keys(Keys.RETURN)
    except (NoSuchElementException, TimeoutException) as e:
        logging.error(f"Error entering data: {e}")

def click_on(element_xpath):
    """
    Click on an element specified by an XPath.
    """
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, element_xpath)))
        element = driver.find_element(By.XPATH, element_xpath)
        if IS_CI:
            # Use JavaScript click in headless mode
            driver.execute_script("arguments[0].click();", element)
        else:
            element.click()
    except (NoSuchElementException, TimeoutException) as e:
        logging.error(f"Error clicking element: {e}")

def initialize():
    """
    Initialize the webdriver, navigate to the login page, and log in.
    """
    try:
        driver.get(r"https://clubspark.lta.org.uk/SouthwarkPark/Account/SignIn?returnUrl=https%3a%2f%2fclubspark.lta.org.uk%2fSouthwarkPark%2fBooking%2fBookByDate")
        time.sleep(3)  # Give page time to load
        
        # Handle cookie consent first
        handle_cookie_consent()
        
        # Click login button
        click_on('/html/body/div[3]/div[1]/div[2]/div[1]/div[2]/form/button')
        time.sleep(1)
        
        # Enter credentials
        enter_data('//*[@id="154:0"]', USERNAME)
        enter_data('//*[@id="input-2"]', PASSWORD)
        
        # Wait for login to complete
        time.sleep(3)
        
    except Exception as e:
        logging.error(f"Error during initialization: {e}")
        # Take screenshot for debugging
        driver.save_screenshot("error_init.png")

def main():
    global driver, wait
    try:
        # Booking time setup
        parsed = urlparse(SAMPLE_URL)
        query = parse_qs(parsed.query)
        query["Date"] = [booking_date.strftime(format='%Y-%m-%d')]
        query["StartTime"] = [str(start_time)]
        query["EndTime"] = [str(start_time + 60)]
        query["ResourceID"] = [resource_ids[court]]
        new_query = urlencode(query, doseq=True)
        booking_url = urlunparse(parsed._replace(query=new_query))
        
        # Wait until specific times to perform actions (uncomment if needed)
        # timer('18:55')
        # timer('18:57')
        # timer('19:00')

        # Initialize the WebDriver
        driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=options)
        wait = WebDriverWait(driver, 10)

        # Login
        initialize()

        # Book
        driver.get(booking_url)
        time.sleep(3)  # Give page time to load
        
        # Handle cookie consent again if it appears
        handle_cookie_consent()
        
        # Pay
        wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="paynow"]')))
        click_on('//*[@id="paynow"]')
        time.sleep(2)

        # Payment process - wait for Stripe elements to load
        wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cs-stripe-elements-card-number"]/div/iframe')))
        time.sleep(2)  # Give Stripe time to fully load
        
        # Enter card details - Stripe uses iframes
        # Card number
        card_frame = driver.find_element(By.XPATH, '//*[@id="cs-stripe-elements-card-number"]/div/iframe')
        driver.switch_to.frame(card_frame)
        card_input = driver.find_element(By.TAG_NAME, 'input')
        card_input.send_keys(CARD_NUMBER)
        driver.switch_to.default_content()
        
        # Card expiry
        expiry_frame = driver.find_element(By.XPATH, '//*[@id="cs-stripe-elements-card-expiry"]/div/iframe')
        driver.switch_to.frame(expiry_frame)
        expiry_input = driver.find_element(By.TAG_NAME, 'input')
        expiry_input.send_keys(CARD_EXPIRY)
        driver.switch_to.default_content()
        
        # Card CVC
        cvc_frame = driver.find_element(By.XPATH, '//*[@id="cs-stripe-elements-card-cvc"]/div/iframe')
        driver.switch_to.frame(cvc_frame)
        cvc_input = driver.find_element(By.TAG_NAME, 'input')
        cvc_input.send_keys(CARD_CVC)
        driver.switch_to.default_content()
        
        # Submit payment
        time.sleep(1)
        click_on('//*[@id="cs-stripe-elements-submit-button"]')
        
        time.sleep(5)
        logging.info("Booking completed!")
        
        # Take success screenshot
        driver.save_screenshot("booking_success.png")
        
    except Exception as e:
        logging.error(f"An error occurred in the main flow: {e}")
        driver.save_screenshot("error_main.png")
    finally:
        time.sleep(5)
        driver.quit()
        logging.info("Done!")

# Define SAMPLE_URL
SAMPLE_URL = 'https://clubspark.lta.org.uk/SouthwarkPark/Booking/Book?Contacts%5B0%5D.IsPrimary=true&Contacts%5B0%5D.IsJunior=false&Contacts%5B0%5D.IsPlayer=true&ResourceID=ad7d3c7b-9dff-4442-bb18-4761970f11c0&Date=2025-06-28&SessionID=c3791901-4d64-48f5-949d-85d01c4633b9&StartTime=1140&EndTime=1200&Category=0&SubCategory=0&VenueID=4123ed12-8dd6-4f48-a706-6ab2fbde16ba&ResourceGroupID=4123ed12-8dd6-4f48-a706-6ab2fbde16ba'

if __name__ == "__main__":    
    main()
