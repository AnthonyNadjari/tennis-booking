import multiprocessing
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import logging
from datetime import datetime

# --------- CONFIGURATION ---------
NUM_COURTS = 4           # Number of courts to brute force in parallel
CONNECTIONS_PER_COURT = 3  # Number of parallel attempts per court (raise for more brute force)
MAX_ATTEMPTS = 200       # Attempts per process
MAX_DURATION = 180       # Max seconds per process

# --------- LOGGING ---------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(processName)s - %(message)s',
    handlers=[
        logging.FileHandler('booking.log'),
        logging.StreamHandler()
    ]
)

def get_env(var, default=None):
    return os.environ.get(var, default)

# --------- BOOKING LOGIC ---------
def run_booking(court_index, process_id=0):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = None

    # Environment/credentials
    account_number = get_env('ACCOUNT', '1')
    if account_number == '2':
        username = get_env('TENNIS_USERNAME2')
    else:
        username = get_env('TENNIS_USERNAME')
    password = get_env('TENNIS_PASSWORD')
    card_number = get_env('CARD_NUMBER', '5354562794845156')
    card_expiry = get_env('CARD_EXPIRY', '04/30')
    card_cvc = get_env('CARD_CVC', '666')
    date = get_env('BOOKING_DATE', '2025-06-16')
    hour = int(get_env('BOOKING_HOUR', '7'))
    minutes = int(get_env('BOOKING_MINUTES', '0'))
    hour_str = f"{hour:02d}:{minutes:02d}"
    target_time_minutes = hour * 60 + minutes

    if not username or not password:
        logging.error("Username or password not set! Exiting.")
        return

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_window_size(1920, 1080)
        logging.info(f"[Court {court_index}][Conn {process_id}] Driver launched")

        # Navigate to booking page
        base_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=guest"
        driver.get(base_url)
        time.sleep(2)

        # Login
        def login():
            try:
                if "My bookings" in driver.page_source or "Log out" in driver.page_source:
                    return True
                # Sign in button
                try:
                    sign_in_link = WebDriverWait(driver, 6).until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in') or contains(@href, 'login')]"))
                    )
                    sign_in_link.click()
                    time.sleep(1)
                except: pass
                # Login button
                try:
                    login_btn = WebDriverWait(driver, 6).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Log in')]"))
                    )
                    login_btn.click()
                    time.sleep(1)
                except: pass
                # Fill credentials
                username_field = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Username' or @name='username' or @id='username']"))
                )
                username_field.clear()
                username_field.send_keys(username)
                password_field = driver.find_element(By.XPATH, "//input[@placeholder='Password' or @name='password' or @id='password' or @type='password']")
                password_field.clear()
                password_field.send_keys(password)
                submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Login') or @type='submit']")
                submit_btn.click()
                time.sleep(2)
                return True
            except Exception as e:
                logging.error(f"[Court {court_index}][Conn {process_id}] Login error: {e}")
                return False

        login_success = login()

        # After login, reload booking page
        driver.get(base_url)
        time.sleep(2)

        # Accept cookies if present
        try:
            cookie_btn = driver.find_element(By.CLASS_NAME, "osano-cm-accept-all")
            cookie_btn.click()
            time.sleep(0.2)
        except:
            pass

        def book_slot():
            # Wait for booking links to appear
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.book-interval"))
                )
            except TimeoutException:
                return False
            # Find all slots
            booking_links = driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked")
            for link in booking_links:
                data_test_id = link.get_attribute('data-test-id') or ""
                # Heuristic: usually format is ...courtIndex|...|minutes
                # Try to match court
                parts = data_test_id.split('|')
                if len(parts) >= 3:
                    try:
                        slot_court_idx = int(parts[1])  # Adjust index if needed
                        slot_time = int(parts[2])
                        if slot_court_idx == court_index and slot_time == target_time_minutes:
                            logging.info(f"[Court {court_index}][Conn {process_id}] Slot found!")
                            link.click()
                            time.sleep(1)
                            return complete_booking()
                    except Exception:
                        continue
            return False

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
                time.sleep(0.3)
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
                logging.error(f"[Court {court_index}][Conn {process_id}] Booking error: {e}")
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
                    logging.info(f"[Court {court_index}][Conn {process_id}] Booking confirmed!")
                    return True
                except:
                    # Check for success indicators
                    time.sleep(5)
                    page_source = driver.page_source.lower()
                    if any(word in page_source for word in ["confirmed", "success", "booked", "reserved", "confirmation"]):
                        logging.info(f"[Court {court_index}][Conn {process_id}] Booking probably confirmed!")
                        return True
                    else:
                        return False
            except Exception as e:
                logging.error(f"[Court {court_index}][Conn {process_id}] Stripe error: {e}")
                return False

        # --------- RETRY LOOP ---------
        start_time = time.time()
        attempt = 0
        while attempt < MAX_ATTEMPTS and (time.time() - start_time) < MAX_DURATION:
            attempt += 1
            logging.info(f"[Court {court_index}][Conn {process_id}] Attempt {attempt}")
            if book_slot():
                logging.info(f"[Court {court_index}][Conn {process_id}] BOOKING SUCCESSFUL!")
                return
            else:
                time.sleep(0.3)
                driver.refresh()
                time.sleep(0.3)
        logging.info(f"[Court {court_index}][Conn {process_id}] Finished without success after {attempt} attempts.")
    except Exception as e:
        logging.error(f"[Court {court_index}][Conn {process_id}] Critical error: {e}")
    finally:
        if driver:
            driver.quit()
            logging.info(f"[Court {court_index}][Conn {process_id}] Driver closed.")

# --------- PARALLEL EXECUTION ---------
if __name__ == "__main__":
    jobs = []
    for court_index in range(1, NUM_COURTS + 1):
        for process_id in range(1, CONNECTIONS_PER_COURT + 1):
            p = multiprocessing.Process(target=run_booking, args=(court_index, process_id))
            p.start()
            jobs.append(p)
    for job in jobs:
        job.join()
