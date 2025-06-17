import os
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking.log'),
        logging.StreamHandler()
    ]
)

# Configure Chrome options
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

# Environment variables
account_number = os.environ.get('ACCOUNT', '1')
username = os.environ.get('TENNIS_USERNAME2') if account_number == '2' else os.environ.get('TENNIS_USERNAME')
password = os.environ.get('TENNIS_PASSWORD')
card_number = os.environ.get('CARD_NUMBER', '5354562794845156')
card_expiry = os.environ.get('CARD_EXPIRY', '04/30')
card_cvc = os.environ.get('CARD_CVC', '666')
date = os.environ.get('BOOKING_DATE', '2023-10-16')
hour = int(os.environ.get('BOOKING_HOUR', '7'))
minutes = int(os.environ.get('BOOKING_MINUTES', '0'))

if not username or not password:
    logging.error("Username or password not defined!")
    exit(1)

# Calculate total minutes and format display
total_minutes = (hour * 60) + minutes
hour_system_minutes = total_minutes
hour_str = f"{hour:02d}:{minutes:02d}"

logging.info(f"Booking for {date} at {hour_str}")
logging.info(f"System minutes: {hour_system_minutes}")
logging.info(f"Account: {account_number} ({'Primary' if account_number == '1' else 'Secondary'})")

# Initialize driver
driver = None

def take_screenshot(name):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{name}_{timestamp}.png"
        driver.save_screenshot(filename)
        logging.info(f"Screenshot saved: {filename}")
    except Exception as e:
        logging.error(f"Screenshot error: {e}")

def login(username, password):
    try:
        current_page = driver.page_source
        if "My bookings" in current_page or "Log out" in current_page:
            logging.info("Already logged in!")
            return True

        logging.info("Logging in...")

        sign_in_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in') or contains(@href, 'login')]"))
        )
        sign_in_link.click()
        logging.info("Clicked on Sign in")

        login_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Log in')]"))
        )
        login_btn.click()
        logging.info("Clicked on Login")

        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Username' or @name='username' or @id='username']"))
        )
        username_field.clear()
        username_field.send_keys(username)
        logging.info("Username entered")

        password_field = driver.find_element(By.XPATH, "//input[@placeholder='Password' or @name='password' or @id='password' or @type='password']")
        password_field.clear()
        password_field.send_keys(password)
        logging.info("Password entered")

        submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Login') or @type='submit']")
        submit_btn.click()
        logging.info("Login submitted")

        time.sleep(2)
        return True

    except Exception as e:
        logging.error(f"Login error: {e}")
        take_screenshot("login_error")
        return False

def wait_for_page_load():
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.book-interval"))
        )
        time.sleep(0.5)
        logging.info("Booking page loaded")
        return True
    except TimeoutException:
        logging.warning("Timeout while loading the page")
        return False

def find_and_book_slot():
    try:
        if not wait_for_page_load():
            return False

        logging.info(f"Searching for slots at {hour_str}...")

        target_time_minutes = hour * 60 + minutes
        xpath_query = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{target_time_minutes}')]"

        try:
            target_slot = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, xpath_query))
            )
            logging.info(f"Slot found at {hour_str}!")
            target_slot.click()
            logging.info("Slot clicked!")
            time.sleep(1.5)
            return complete_booking_process()

        except TimeoutException:
            logging.info("Direct search failed, trying classic method...")

            booking_links = driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked")

            for link in booking_links:
                data_test_id = link.get_attribute('data-test-id') or ""
                if '|' in data_test_id:
                    parts = data_test_id.split('|')
                    if len(parts) >= 3 and int(parts[2]) == target_time_minutes:
                        logging.info(f"Slot found at {hour_str}!")
                        link.click()
                        time.sleep(1.5)
                        return complete_booking_process()

        logging.warning(f"No slot found for {hour_str}")
        return False

    except Exception as e:
        logging.error(f"Error: {e}")
        return False

def complete_booking_process():
    try:
        time.sleep(0.5)

        try:
            select2_dropdown = driver.find_element(By.CSS_SELECTOR, ".select2-selection, .select2-selection--single")
            select2_dropdown.click()
            time.sleep(0.2)

            options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
            if len(options) >= 2:
                options[1].click()
                logging.info("Duration selected")
        except:
            try:
                duration_select = driver.find_element(By.ID, "booking-duration")
                Select(duration_select).select_by_index(1)
                logging.info("Duration selected")
            except:
                pass

        time.sleep(0.3)

        try:
            continue_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
            continue_btn.click()
            logging.info("Continue clicked")
            time.sleep(2)
        except:
            try:
                continue_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
                continue_btn.click()
                logging.info("Continue clicked (submit)")
                time.sleep(1)
            except:
                logging.error("Continue button not found")
                return False

        try:
            time.sleep(1)
            pay_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "paynow"))
            )
            pay_btn.click()
            logging.info("Confirm and pay clicked")
            time.sleep(1)
        except:
            try:
                pay_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm and pay')]")
                pay_btn.click()
                logging.info("Confirm and pay clicked (by text)")
                time.sleep(1)
            except:
                logging.error("Confirm and pay button not found")
                take_screenshot("pay_button_not_found")
                return False

        return handle_stripe_payment()

    except Exception as e:
        logging.error(f"Booking error: {e}")
        return False

def handle_stripe_payment():
    try:
        logging.info("Processing Stripe payment...")

        time.sleep(2)

        try:
            iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']")

            if len(iframes) >= 3:
                logging.info(f"{len(iframes)} Stripe iframes found - inline payment")

                driver.switch_to.frame(iframes[0])
                card_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cardnumber']"))
                )
                card_field.clear()
                card_field.send_keys(card_number)
                driver.switch_to.default_content()
                logging.info("Card number entered")

                driver.switch_to.frame(iframes[1])
                expiry_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='exp-date']"))
                )
                expiry_field.clear()
                expiry_field.send_keys(card_expiry)
                driver.switch_to.default_content()
                logging.info("Expiry date entered")

                driver.switch_to.frame(iframes[2])
                cvc_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cvc']"))
                )
                cvc_field.clear()
                cvc_field.send_keys(card_cvc)
                driver.switch_to.default_content()
                logging.info("CVC entered")

                submit_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
                time.sleep(0.5)
                submit_btn.click()
                logging.info("Payment submitted")

            else:
                logging.info("Looking for Stripe Checkout...")
                checkout_iframe = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[name='stripe_checkout_app']"))
                )
                logging.info("Stripe Checkout found")
                driver.switch_to.frame(checkout_iframe)

                card_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Card number']"))
                )
                card_input.send_keys(card_number)

                expiry_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='MM / YY']")
                expiry_input.send_keys(card_expiry)

                cvc_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='CVC']")
                cvc_input.send_keys(card_cvc)

                submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                submit_btn.click()

                driver.switch_to.default_content()
                logging.info("Checkout payment submitted")

        except Exception as e:
            logging.error(f"Error detecting payment type: {e}")
            take_screenshot("stripe_detection_error")
            return False

        try:
            WebDriverWait(driver, 30).until(
                lambda d: "confirmation" in d.current_url.lower() or "success" in d.current_url.lower()
            )
            take_screenshot("confirmation")
            logging.info("Booking confirmed!")
            return True
        except:
            time.sleep(5)
            page_source = driver.page_source.lower()
            if any(word in page_source for word in ["confirmed", "success", "booked", "reserved", "confirmation", "thank you"]):
                logging.info("Booking probably confirmed!")
                take_screenshot("probable_success")
                return True
            else:
                logging.error("No confirmation found")
                take_screenshot("no_confirmation")
                return False

    except Exception as e:
        logging.error(f"Stripe payment error: {e}")
        take_screenshot("stripe_error")
        return False

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_size(1920, 1080)
    logging.info("Driver initialized")

    base_urls = [
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=guest",
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate?date={date}",
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/Calendar?date={date}",
        "https://clubspark.lta.org.uk/SouthwarkPark/Booking"
    ]

    url_success = False
    for url in base_urls:
        try:
            logging.info(f"Navigating to: {url}")
            driver.get(url)
            time.sleep(3)

            if "booking" in driver.current_url.lower() or "calendar" in driver.current_url.lower():
                url_success = True
                logging.info(f"URL successful: {url}")
                break
        except:
            continue

    if not url_success:
        logging.error("Unable to navigate to the booking page")
        exit(1)

    take_screenshot("initial_page")

    login_success = login(username, password)
    is_logged_in = login_success

    if login_success:
        logging.info("Login successful - Optimized mode activated")
        driver.get(base_urls[0])
        time.sleep(3)
    else:
        logging.warning("Login failed, continuing...")

    attempt = 0
    max_attempts = 300 if is_logged_in else 10
    start_time = time.time()
    max_duration = 300

    while attempt < max_attempts and (time.time() - start_time) < max_duration:
        attempt += 1
        elapsed = int(time.time() - start_time)
        logging.info(f"Attempt {attempt}/{max_attempts} (time: {elapsed}s)")

        if find_and_book_slot():
            logging.info("Booking successful!")
            break
        else:
            if attempt < max_attempts and (time.time() - start_time) < max_duration - 10:
                refresh_delay = 0.5 if is_logged_in else 1.5
                time.sleep(refresh_delay)
                driver.refresh()
                time.sleep(0.5)
            else:
                break

    total_time = int(time.time() - start_time)
    logging.info(f"Script completed in {total_time}s after {attempt} attempts")

except Exception as e:
    logging.error(f"Critical error: {e}")
    if driver:
        take_screenshot("critical_error")
finally:
    if driver:
        driver.quit()
        logging.info("Driver closed")
