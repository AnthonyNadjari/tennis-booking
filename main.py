import multiprocessing
import time
import os
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# ---------- CONFIGURATION ----------
NUM_COURTS = 4  # Number of courts to brute force in parallel
ATTEMPTS_PER_COURT = 200  # Number of attempts per process
MAX_SECONDS_PER_COURT = 180  # Max seconds per process

# ---------- LOGGING SETUP ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking.log'),
        logging.StreamHandler()
    ]
)

# ---------- CHROMEDRIVER PRE-DOWNLOAD ----------
def get_chromedriver_path():
    # Download the driver once, then reuse among processes
    return ChromeDriverManager().install()

# ---------- BOOKING LOGIC ----------
def book_court(court_index, chromedriver_path):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = None

    # Credentials and booking information
    username = os.environ.get('TENNIS_USERNAME')
    password = os.environ.get('TENNIS_PASSWORD')
    card_number = os.environ.get('CARD_NUMBER', '5354562794845156')
    card_expiry = os.environ.get('CARD_EXPIRY', '04/30')
    card_cvc = os.environ.get('CARD_CVC', '666')
    date = os.environ.get('BOOKING_DATE', '2025-06-16')
    hour = int(os.environ.get('BOOKING_HOUR', '7'))
    minutes = int(os.environ.get('BOOKING_MINUTES', '0'))
    target_time_minutes = hour * 60 + minutes

    booking_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate?date={date}"

    def login():
        try:
            driver.get(booking_url)
            time.sleep(2)
            # Click Sign in
            try:
                sign_in = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in') or contains(@href, 'login')]"))
                )
                sign_in.click()
                time.sleep(1)
            except Exception:
                pass
            # Click Login button if present
            try:
                login_btn = WebDriverWait(driver, 7).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Log in')]"))
                )
                login_btn.click()
                time.sleep(1)
            except Exception:
                pass
            # Fill credentials
            username_field = WebDriverWait(driver, 7).until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@name,'username')]"))
            )
            username_field.clear()
            username_field.send_keys(username)
            password_field = driver.find_element(By.XPATH, "//input[contains(@name,'password')]")
            password_field.clear()
            password_field.send_keys(password)
            submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Login') or @type='submit']")
            submit_btn.click()
            time.sleep(3)
            return True
        except Exception as e:
            logging.error(f"Court {court_index}: Login failed: {e}")
            return False

    def find_slot():
        try:
            slots = driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked")
            for link in slots:
                data_test_id = link.get_attribute('data-test-id') or ""
                # Expect format "...|court_index|target_time_minutes"
                parts = data_test_id.split('|')
                if len(parts) >= 3:
                    try:
                        slot_court = int(parts[1])
                        slot_time = int(parts[2])
                        if slot_court == court_index and slot_time == target_time_minutes:
                            return link
                    except Exception:
                        continue
            return None
        except Exception as e:
            logging.error(f"Court {court_index}: Error finding slot: {e}")
            return None

    def complete_booking():
        try:
            # Select duration (try select2 dropdown first)
            try:
                select2_dropdown = driver.find_element(By.CSS_SELECTOR, ".select2-selection, .select2-selection--single")
                select2_dropdown.click()
                time.sleep(0.2)
                options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
                if len(options) >= 2:
                    options[1].click()
            except:
                try:
                    duration_select = driver.find_element(By.ID, "booking-duration")
                    Select(duration_select).select_by_index(1)
                except:
                    pass
            time.sleep(0.2)
            # Continue
            try:
                continue_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
                continue_btn.click()
                time.sleep(1)
            except:
                try:
                    continue_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
                    continue_btn.click()
                    time.sleep(1)
                except:
                    return False
            # Pay Now
            try:
                pay_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.ID, "paynow"))
                )
                pay_btn.click()
                time.sleep(1)
            except:
                return False
            # Stripe payment
            return handle_stripe_payment()
        except Exception as e:
            logging.error(f"Court {court_index}: Booking error: {e}")
            return False

    def handle_stripe_payment():
        try:
            iframes = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
            )
            if len(iframes) < 3:
                return False
            # Card number
            driver.switch_to.frame(iframes[0])
            card_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cardnumber'], input[placeholder*='card'], input[data-elements-stable-field-name='cardNumber']"))
            )
            card_field.clear()
            card_field.send_keys(card_number)
            driver.switch_to.default_content()
            # Expiry
            driver.switch_to.frame(iframes[1])
            expiry_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='exp-date'], input[placeholder*='MM'], input[data-elements-stable-field-name='cardExpiry']"))
            )
            expiry_field.clear()
            expiry_field.send_keys(card_expiry)
            driver.switch_to.default_content()
            # CVC
            driver.switch_to.frame(iframes[2])
            cvc_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cvc'], input[placeholder*='CVC'], input[data-elements-stable-field-name='cardCvc']"))
            )
            cvc_field.clear()
            cvc_field.send_keys(card_cvc)
            driver.switch_to.default_content()
            # Submit payment
            submit_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
            time.sleep(0.5)
            submit_btn.click()
            # Wait for confirmation
            try:
                WebDriverWait(driver, 30).until(
                    lambda d: "confirmation" in d.current_url.lower() or "success" in d.current_url.lower()
                )
                logging.info(f"Court {court_index}: Booking confirmed!")
                return True
            except:
                # Check for success indicators
                time.sleep(5)
                page_source = driver.page_source.lower()
                if any(word in page_source for word in ["confirmed", "success", "booked", "reserved", "confirmation"]):
                    logging.info(f"Court {court_index}: Booking probably confirmed!")
                    return True
                else:
                    return False
        except Exception as e:
            logging.error(f"Court {court_index}: Stripe error: {e}")
            return False

    # MAIN EXECUTION PER COURT
    try:
        driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
        driver.set_window_size(1920, 1080)
        if not login():
            logging.error(f"Court {court_index}: Login failed, aborting.")
            driver.quit()
            return
        driver.get(booking_url)
        time.sleep(2)

        attempts = 0
        start_time = time.time()
        while attempts < ATTEMPTS_PER_COURT and (time.time() - start_time) < MAX_SECONDS_PER_COURT:
            attempts += 1
            slot = find_slot()
            if slot:
                try:
                    slot.click()
                    logging.info(f"Court {court_index}: Slot clicked! Attempting booking...")
                    if complete_booking():
                        logging.info(f"Court {court_index}: BOOKING SUCCESSFUL!")
                        driver.quit()
                        return
                except Exception as e:
                    logging.error(f"Court {court_index}: Click failed: {e}")
            else:
                if attempts % 10 == 0:
                    logging.info(f"Court {court_index}: Attempt {attempts} - no slot yet.")
                try:
                    driver.refresh()
                except WebDriverException:
                    break
                time.sleep(0.2)
        logging.info(f"Court {court_index}: Finished after {attempts} attempts, no booking.")
    except Exception as e:
        logging.error(f"Court {court_index}: Critical error: {e}")
    finally:
        if driver:
            driver.quit()
            logging.info(f"Court {court_index}: Driver closed.")

# ---------- PARALLEL EXECUTION ----------
if __name__ == "__main__":
    chromedriver_path = get_chromedriver_path()
    procs = []
    for court_idx in range(1, NUM_COURTS + 1):
        p = multiprocessing.Process(target=book_court, args=(court_idx, chromedriver_path))
        p.start()
        procs.append(p)
    for p in procs:
        p.join()
