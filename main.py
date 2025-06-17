from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import logging
from datetime import datetime
import random

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking.log'),
        logging.StreamHandler()
    ]
)

# Chrome Configuration
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

# Environment Variables
account_number = os.environ.get('ACCOUNT', '1')
username = os.environ.get('TENNIS_USERNAME2') if account_number == '2' else os.environ.get('TENNIS_USERNAME')
password = os.environ.get('TENNIS_PASSWORD')
card_number = os.environ.get('CARD_NUMBER', '5354562794845156')
card_expiry = os.environ.get('CARD_EXPIRY', '04/30')
card_cvc = os.environ.get('CARD_CVC', '666')
date = os.environ.get('BOOKING_DATE', '2025-06-16')
hour = int(os.environ.get('BOOKING_HOUR', '7'))
minutes = int(os.environ.get('BOOKING_MINUTES', '0'))

if not username or not password:
    logging.error("❌ Username or password not defined!")
    exit(1)

total_minutes = (hour * 60) + minutes
hour_str = f"{hour:02d}:{minutes:02d}"

logging.info(f"🎾 Booking for {date} at {hour_str}")
logging.info(f"👤 Account: {account_number} ({'Primary' if account_number == '1' else 'Secondary'})")

# Initialize driver - GLOBAL VARIABLE
driver = None
try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_size(1920, 1080)
    logging.info("✅ Driver initialized")
except Exception as e:
    logging.error(f"❌ Driver error: {e}")
    exit(1)


def take_screenshot(name):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{name}_{timestamp}.png"
        driver.save_screenshot(filename)
        logging.info(f"📸 Screenshot saved: {filename}")
    except Exception as e:
        logging.error(f"Screenshot error: {e}")


def login_first(username, password):
    try:
        current_page = driver.page_source
        if "My bookings" in current_page or "Log out" in current_page:
            logging.info("✅ Already logged in!")
            return True

        logging.info("🔐 Logging in...")

        # Click Sign in
        try:
            sign_in_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in') or contains(@href, 'login')]"))
            )
            sign_in_link.click()
            logging.info("✅ Clicked Sign in")
            time.sleep(1)
        except Exception as e:
            logging.warning(f"Sign in link not found: {e}")

        # Fill credentials and login
        try:
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@name='username' or @id='username']"))
            )
            username_field.clear()
            username_field.send_keys(username)
            logging.info("✅ Entered username")

            password_field = driver.find_element(By.XPATH, "//input[@type='password']")
            password_field.clear()
            password_field.send_keys(password)
            logging.info("✅ Entered password")

            submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in') or @type='submit']")
            submit_btn.click()
            logging.info("✅ Submitted login")

            time.sleep(2)
            return True

        except Exception as e:
            logging.error(f"Error entering credentials: {e}")
            return False

    except Exception as e:
        logging.error(f"❌ Login error: {e}")
        take_screenshot("login_error")
        return False


def wait_for_page_load():
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.book-interval"))
        )
        time.sleep(0.5)  # Wait for dynamic content
        logging.info("✅ Booking page loaded")
        return True
    except TimeoutException:
        logging.warning("⚠️ Page load timeout")
        return False


def find_and_book_slot():
    try:
        if not wait_for_page_load():
            return False

        logging.info(f"🔍 Searching slots for {hour_str} across all courts...")
        xpath_query = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{total_minutes}') and not(contains(@class, 'disabled'))]"

        available_slots = driver.find_elements(By.XPATH, xpath_query)

        if available_slots:
            for slot in available_slots:
                try:
                    logging.info(f"🎯 Found slot at {hour_str}!")
                    slot.click()
                    time.sleep(1.5)
                    return complete_booking_process()
                except ElementClickInterceptedException:
                    logging.warning("⚠️ Slot click intercepted, trying next")
                    continue

        logging.warning(f"⚠️ No slots available for {hour_str}")
        return False

    except Exception as e:
        logging.error(f"❌ Error: {e}")
        return False


def complete_booking_process():
    try:
        # Select duration
        try:
            duration_select = driver.find_element(By.ID, "booking-duration")
            Select(duration_select).select_by_index(1)
            logging.info("✅ Duration selected")
        except:
            pass

        # Click Continue
        try:
            continue_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
            continue_btn.click()
            logging.info("✅ Clicked Continue")
            time.sleep(1)
        except:
            logging.error("❌ Continue button not found")
            return False

        # Click Pay Now
        try:
            pay_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, "paynow"))
            )
            pay_btn.click()
            logging.info("✅ Clicked Pay Now")
            time.sleep(1)
        except:
            logging.error("❌ Pay Now button not found")
            return False

        return handle_stripe_payment()

    except Exception as e:
        logging.error(f"❌ Booking process error: {e}")
        return False


def handle_stripe_payment():
    try:
        logging.info("💳 Processing Stripe payment...")
        take_screenshot("stripe_form")

        # Handle payment fields
        iframes = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
        )
        if len(iframes) < 3:
            logging.error("❌ Insufficient Stripe iframes")
            return False

        # Card number
        driver.switch_to.frame(iframes[0])
        card_field = driver.find_element(By.CSS_SELECTOR, "input[name='cardnumber']")
        card_field.send_keys(card_number)
        driver.switch_to.default_content()

        # Expiry date
        driver.switch_to.frame(iframes[1])
        expiry_field = driver.find_element(By.CSS_SELECTOR, "input[name='exp-date']")
        expiry_field.send_keys(card_expiry)
        driver.switch_to.default_content()

        # CVC
        driver.switch_to.frame(iframes[2])
        cvc_field = driver.find_element(By.CSS_SELECTOR, "input[name='cvc']")
        cvc_field.send_keys(card_cvc)
        driver.switch_to.default_content()

        # Submit payment
        submit_btn = driver.find_element(By.ID, "cs-stripe-elements-submit-button")
        submit_btn.click()
        logging.info("✅ Payment submitted")

        WebDriverWait(driver, 20).until(
            lambda d: "confirmation" in d.current_url.lower() or "success" in d.current_url.lower()
        )
        take_screenshot("confirmation")
        logging.info("🎉 Booking confirmed!")
        return True

    except Exception as e:
        logging.error(f"❌ Stripe payment error: {e}")
        take_screenshot("stripe_error")
        return False


# Main Execution
try:
    start_time = time.time()
    base_urls = [
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=guest",
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/Calendar?date={date}",
    ]

    driver.get(base_urls[0])
    if not login_first(username, password):
        logging.error("❌ Login failed")
        exit(1)

    while True:
        if find_and_book_slot():
            break
        time.sleep(random.uniform(0.5, 1.0))  # Randomized delay
        driver.refresh()

    logging.info("✅ Script completed")

except Exception as e:
    logging.error(f"❌ Critical error: {e}")
    take_screenshot("critical_error")
finally:
    if driver:
        driver.quit()
        logging.info("🏁 Driver closed")
