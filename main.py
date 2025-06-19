from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import logging
from datetime import datetime
# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tennis_booking.log'),
        logging.StreamHandler()
    ]
)
# Configuration Chrome
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Remove this line if you want to see the browser
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.page_load_strategy = 'eager'
# Environment Variables Configuration
username = os.environ.get('TENNIS_USERNAME')  # Default fallback
password = os.environ.get('TENNIS_PASSWORD')  # Default fallback
card_number = os.environ.get('CARD_NUMBER')
card_expiry = os.environ.get('CARD_EXPIRY')
card_cvc = os.environ.get('CARD_CVC')
booking_day = os.environ.get('BOOKING_DATE')
booking_hour = int(os.environ.get('BOOKING_HOUR'))  # 7 PM = 19 in 24h format
booking_minutes = int(os.environ.get('BOOKING_MINUTES'))

# Validation
if not username or not password:
    logging.error("❌ Username or password not defined!")
    exit(1)

# Calculate target time
target_time_minutes = booking_hour * 60 + booking_minutes
hour_str = f"{booking_hour:02d}:{booking_minutes:02d}"

logging.info(f"🎾 Tennis booking for day {booking_day} at {hour_str}")
logging.info(f"⏰ Target time in minutes: {target_time_minutes}")
logging.info(f"👤 Username: {username}")
# Initialize driver
driver = None

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_size(1920, 1080)
    wait = WebDriverWait(driver, 10)
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

def enter_data(xpath, keys):
    try:
        element = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
        element.clear()
        element.send_keys(keys, Keys.RETURN)
        return True
    except Exception as e:
        logging.error(f"Error entering data in {xpath}: {e}")
        return False

def click_on(xpath):
    try:
        element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        element.click()
        return True
    except Exception as e:
        logging.error(f"Error clicking {xpath}: {e}")
        return False


def login_process():
    try:
        logging.info("🔐 Starting login process...")

        # Navigate to login page
        driver.get(
            "https://clubspark.lta.org.uk/SouthwarkPark/Account/SignIn?returnUrl=https%3a%2f%2fclubspark.lta.org.uk%2fSouthwarkPark%2fBooking%2fBookByDate")

        # Click login button
        if not click_on('/html/body/div[3]/div[1]/div[2]/div[1]/div[2]/form/button'):
            return False

        # Enter credentials
        if not enter_data('//*[@id="154:0"]', username):
            return False

        if not enter_data('//*[@id="input-2"]', password):
            return False

        logging.info("✅ Login completed")
        take_screenshot("afterbooking")
        time.sleep(2)
        return True

    except Exception as e:
        logging.error(f"❌ Login error: {e}")
        take_screenshot("login_error")
        return False


def select_date():
    try:
        booking_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={booking_day}&role=member"
        logging.info(f"🌐 Navigation vers: {booking_url}")
        driver.get(booking_url)
        time.sleep(3)
        logging.info("✅ Date selected via URL")
        return True
        
    except Exception as e:
        logging.error(f"❌ Date selection error: {e}")
        return False


def find_and_book_slot():
    try:
        logging.info(f"🔍 Looking for slot at {hour_str} ({target_time_minutes} minutes)")

        # Refresh and wait for booking links
        driver.refresh()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'a.book-interval')))

        # Retry logic - max 5 minutes
        start_time = time.time()
        max_duration = 5 * 60  # 5 minutes in seconds
        attempt = 0

        while time.time() - start_time < max_duration:
            attempt += 1
            elapsed = int(time.time() - start_time)
            logging.info(f"🔄 Attempt {attempt} (elapsed: {elapsed}s)")

            # Try direct XPath targeting first
            xpath_query = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{target_time_minutes}')]"

            try:
                target_slot = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, xpath_query))
                )
                logging.info(f"🎯 SLOT FOUND DIRECTLY at {hour_str}!")
                target_slot.click()
                logging.info("✅ Clicked!")
                return True

            except TimeoutException:
                logging.info("⚠️ Direct search failed, trying fallback method...")

                # Fallback: search through all available slots
                booking_links = driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked")

                for link in booking_links:
                    data_test_id = link.get_attribute('data-test-id') or ""

                    if '|' in data_test_id:
                        parts = data_test_id.split('|')
                        if len(parts) >= 3:
                            try:
                                slot_time = int(parts[2])
                                if slot_time == target_time_minutes:
                                    logging.info(f"🎯 SLOT FOUND at {hour_str}!")
                                    link.click()
                                    return True
                            except:
                                continue

                # If no slot found and still have time, refresh and try again
                remaining_time = max_duration - (time.time() - start_time)
                if remaining_time > 10:
                    logging.info(f"❌ No slot found, refreshing... ({int(remaining_time)}s remaining)")
                    driver.refresh()
                    time.sleep(0.5)
                    try:
                        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'a.book-interval')))
                    except:
                        logging.warning("⚠️ Page load timeout, continuing...")
                else:
                    logging.info("⏰ Time limit reached, stopping search")
                    break

        logging.error(f"❌ No slot found for {hour_str} after 5 minutes")
        return False

    except Exception as e:
        logging.error(f"❌ Slot booking error: {e}")
        take_screenshot("slot_booking_error")
        return False


def complete_booking():
    try:
        logging.info("💳 Completing booking process...")

        # Select duration
        if not click_on('/html/body/div[8]/div/div/div/div[1]/form/div[1]/div[1]/div[2]/div/div/div/span'):
            return False
        if not click_on('/html/body/span/span/span[2]/ul/li[2]'):
            return False

        # Submit booking
        if not click_on('//*[@id="submit-booking"]'):
            return False

        # Pay now
        if not click_on('//*[@id="paynow"]'):
            return False

        time.sleep(1)

        # Fill payment details
        payment_fields = [
            ('//*[@id="cs-stripe-elements-card-number"]/div/iframe', card_number),
            ('//*[@id="cs-stripe-elements-card-expiry"]/div/iframe', card_expiry),
            ('//*[@id="cs-stripe-elements-card-cvc"]/div/iframe', card_cvc)
        ]

        for xpath, value in payment_fields:
            # Clear field multiple times (as in original)
            for _ in range(3):
                enter_data(xpath, '')
            enter_data(xpath, value)

        # Submit payment
        if not click_on('//*[@id="cs-stripe-elements-submit-button"]'):
            return False

        logging.info("✅ Payment submitted")
        time.sleep(5)
        return True

    except Exception as e:
        logging.error(f"❌ Booking completion error: {e}")
        take_screenshot("booking_completion_error")
        return False


# Main execution
try:
    start_time = time.time()

    # Login
    if not login_process():
        logging.error("❌ Login failed")
        exit(1)

    # Select date
    if not select_date():
        logging.error("❌ Date selection failed")
        exit(1)

    # Find and book slot
    if not find_and_book_slot():
        logging.error("❌ Slot booking failed")
        exit(1)

    # Complete booking
    if not complete_booking():
        logging.error("❌ Booking completion failed")
        exit(1)

    total_time = int(time.time() - start_time)
    logging.info(f"🎉 Booking process completed successfully in {total_time}s!")

except Exception as e:
    logging.error(f"❌ Critical error: {e}")
    if driver:
        take_screenshot("critical_error")
finally:
    if driver:
        driver.quit()
        logging.info("🏁 Driver closed")