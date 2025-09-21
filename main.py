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
ACCOUNT_NUMBER = os.environ.get('ACCOUNT')
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
logging.info(
    f"🔑 Utilisation du compte {'secondaire' if ACCOUNT_NUMBER == '2' else 'principal'} (TENNIS_USERNAME{'2' if ACCOUNT_NUMBER == '2' else ''})")

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

# Configuration Chrome
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.page_load_strategy = 'eager'


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
        time.sleep(wait_seconds)


def enter_data(element_xpath, input_text):
    """Enter data into a field specified by an XPath and send a return key."""
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, element_xpath)))
        driver.find_element(By.XPATH, element_xpath).send_keys(input_text, Keys.RETURN)
    except (NoSuchElementException, TimeoutException) as e:
        logging.error(f"Error entering data: {e}")


def click_on(element_xpath):
    """Click on an element specified by an XPath."""
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, element_xpath)))
        driver.find_element(By.XPATH, element_xpath).click()
    except (NoSuchElementException, TimeoutException) as e:
        logging.error(f"Error clicking element: {e}")


def wait_for(element_xpath):
    """Wait for an element to be clickable."""
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, element_xpath)))
    except TimeoutException as e:
        logging.error(f"Timeout waiting for element: {e}")


def initialize():
    """Initialize the webdriver, navigate to the login page, and log in."""
    try:
        driver.get(
            r"https://clubspark.lta.org.uk/SouthwarkPark/Account/SignIn?returnUrl=https%3a%2f%2fclubspark.lta.org.uk%2fSouthwarkPark%2fBooking%2fBookByDate")
        click_on('/html/body/div[3]/div[1]/div[2]/div[1]/div[2]/form/button')
        enter_data('//*[@id="154:0"]', USERNAME)
        enter_data('//*[@id="input-2"]', PASSWORD)

        # Handle cookie dialog
        try:
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.osano-cm-dialog__close.osano-cm-close')))
            driver.find_element(By.CSS_SELECTOR, 'button.osano-cm-dialog__close.osano-cm-close').click()
            logging.info("Successfully closed cookie dialog")
        except Exception as e:
            logging.info("No cookie dialog found or error closing it: " + str(e))

        time.sleep(5)

    except Exception as e:
        logging.error(f"Error during initialization: {e}")


def handle_payment():
    """Handle the payment process with iframe switching."""
    try:
        # Wait for and click pay now button
        wait_for('//*[@id="paynow"]')
        click_on('//*[@id="paynow"]')

        # Handle card number iframe
        wait_for('//*[@id="cs-stripe-elements-card-number"]/div/iframe')
        card_number_iframe = driver.find_element(By.XPATH, '//*[@id="cs-stripe-elements-card-number"]/div/iframe')
        driver.switch_to.frame(card_number_iframe)
        wait_for('//*[@id="root"]/form/span[2]/div/div/div[2]/span/input')
        input_field = driver.find_element(By.XPATH, '//*[@id="root"]/form/span[2]/div/div/div[2]/span/input')
        input_field.clear()
        input_field.send_keys(CARD_NUMBER)
        driver.switch_to.default_content()
        logging.info("Card number entered successfully")

        # Handle card expiry iframe
        card_expiry_iframe = driver.find_element(By.XPATH, '//*[@id="cs-stripe-elements-card-expiry"]/div/iframe')
        driver.switch_to.frame(card_expiry_iframe)
        wait_for('//*[@id="root"]/form/span[2]/div/span/input')
        input_field = driver.find_element(By.XPATH, '//*[@id="root"]/form/span[2]/div/span/input')
        input_field.clear()
        input_field.send_keys(CARD_EXPIRY)
        driver.switch_to.default_content()
        logging.info("Card expiry entered successfully")

        # Handle CVC iframe
        cvc_iframe = driver.find_element(By.XPATH, '//*[@id="cs-stripe-elements-card-cvc"]/div/iframe')
        driver.switch_to.frame(cvc_iframe)
        wait_for('//*[@id="root"]/form/span[2]/div/span/input')
        input_field = driver.find_element(By.XPATH, '//*[@id="root"]/form/span[2]/div/span/input')
        input_field.clear()
        input_field.send_keys(CARD_CVC)
        driver.switch_to.default_content()
        logging.info("CVC entered successfully")

        # Submit payment
        click_on('//*[@id="cs-stripe-elements-submit-button"]')
        logging.info("Payment submitted")

    except Exception as e:
        logging.error(f"Error during payment process: {e}")


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

        # Wait until specific times to perform actions
        timer('18:55')  # because git is late

        # Initialize the WebDriver
        driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=options)
        wait = WebDriverWait(driver, 10)

        # Login
        timer('18:57')
        initialize()

        # Book
        timer('19:00')
        driver.get(booking_url)
        logging.info(f"Navigated to booking URL: {booking_url}")

        # Handle payment
        handle_payment()

        # Wait for payment completion
        time.sleep(10)
        logging.info("Payment process completed")

    except Exception as e:
        logging.error(f"An error occurred in the main flow: {e}")
    finally:
        timer('19:05')
        logging.info("Done!")
        if 'driver' in globals():
            driver.quit()


# Define SAMPLE_URL
SAMPLE_URL = 'https://clubspark.lta.org.uk/SouthwarkPark/Booking/Book?Contacts%5B0%5D.IsPrimary=true&Contacts%5B0%5D.IsJunior=false&Contacts%5B0%5D.IsPlayer=true&ResourceID=ad7d3c7b-9dff-4442-bb18-4761970f11c0&Date=2025-06-28&SessionID=16809b9a-4d22-4b9a-8198-3f1c52a20497&StartTime=1140&EndTime=1200&Category=0&SubCategory=0&VenueID=4123ed12-8dd6-4f48-a706-6ab2fbde16ba&ResourceGroupID=4123ed12-8dd6-4f48-a706-6ab2fbde16ba'

if __name__ == "__main__":
    main()
