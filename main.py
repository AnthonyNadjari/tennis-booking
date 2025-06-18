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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking.log'),
        logging.StreamHandler()
    ]
)

# Chrome configuration
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Environment variables
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
hour_system_minutes = total_minutes
hour_str = f"{hour:02d}:{minutes:02d}"

logging.info(f"🎾 Booking for {date} at {hour_str}")
logging.info(f"⏰ System minutes: {hour_system_minutes}")
logging.info(f"👤 Account: {account_number} ({'Primary' if account_number == '1' else 'Secondary'})")

# Initialize driver
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

def check_login_status():
    try:
        page_source = driver.page_source
        logged_in_indicators = ["My bookings", "Log out", "Sign out", "My account", "Account settings"]
        return any(indicator in page_source for indicator in logged_in_indicators)
    except:
        return False

def ensure_logged_in(username, password):
    if check_login_status():
        logging.info("✅ Already logged in!")
        return True

    logging.info("🔐 Not logged in, attempting to log in...")
    return login_first(username, password)

def login_first(username, password):
    try:
        driver.get("https://clubspark.lta.org.uk/SouthwarkPark")
        time.sleep(1)

        try:
            cookie_btn = driver.find_element(By.CLASS_NAME, "osano-cm-accept-all")
            cookie_btn.click()
        except:
            pass

        try:
            sign_in_link = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in') or contains(@href, 'login')]"))
            )
            sign_in_link.click()
        except:
            driver.get("https://clubspark.lta.org.uk/SouthwarkPark/Account/Login")

        try:
            username_field = WebDriverWait(driver, 5).until(
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

            if check_login_status():
                logging.info("✅ Login confirmed!")
                return True
            else:
                logging.error("❌ Login not confirmed")
                take_screenshot("login_failed")
                return False
        except Exception as e:
            logging.error(f"Error entering credentials: {e}")
            take_screenshot("login_error")
            return False
    except Exception as e:
        logging.error(f"❌ Login error: {e}")
        take_screenshot("login_error")
        return False

def find_and_book_slot():
    try:
        if not check_login_status():
            logging.warning("⚠️ Session lost, need to reconnect")
            return False

        try:
            cookie_btn = driver.find_element(By.CLASS_NAME, "osano-cm-accept-all")
            cookie_btn.click()
        except:
            pass

        target_time_minutes = hour * 60 + minutes
        xpath_query = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{target_time_minutes}')]"

        try:
            target_slot = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, xpath_query))
            )
            logging.info(f"🎯 SLOT FOUND DIRECTLY at {hour_str}!")
            target_slot.click()
            time.sleep(1)
            return complete_booking_process()
        except TimeoutException:
            logging.info("⚠️ Direct search failed, using classic method...")

            booking_links = driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked")
            for link in booking_links:
                data_test_id = link.get_attribute('data-test-id') or ""
                if '|' in data_test_id:
                    parts = data_test_id.split('|')
                    if len(parts) >= 3 and int(parts[2]) == target_time_minutes:
                        logging.info(f"🎯 SLOT FOUND at {hour_str}!")
                        link.click()
                        time.sleep(1)
                        return complete_booking_process()

        logging.warning(f"⚠️ No slot found for {hour_str}")
        return False
    except Exception as e:
        logging.error(f"❌ Error: {e}")
        return False

def complete_booking_process():
    try:
        current_url = driver.current_url
        if "login" in current_url.lower() or not check_login_status():
            logging.error("❌ Redirected to login after slot selection!")
            return False

        try:
            select2_dropdown = driver.find_element(By.CSS_SELECTOR, ".select2-selection, .select2-selection--single")
            select2_dropdown.click()
            options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
            if len(options) >= 2:
                options[1].click()
        except:
            try:
                duration_select = driver.find_element(By.ID, "booking-duration")
                Select(duration_select).select_by_index(1)
            except:
                pass

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
                logging.error("❌ Continue button not found")
                return False

        current_url = driver.current_url
        if "login" in current_url.lower():
            logging.error("❌ Redirected to login after Continue!")
            if login_first(username, password):
                logging.info("✅ Re-connected successfully")
                return False
            else:
                logging.error("❌ Unable to reconnect")
                return False

        try:
            pay_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "paynow"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pay_btn)
            pay_btn.click()
            time.sleep(1)
            return handle_stripe_payment()
        except TimeoutException:
            logging.error("❌ Payment button not found")
            return False
    except Exception as e:
        logging.error(f"❌ Booking error: {e}")
        return False

def handle_stripe_payment():
    try:
        if "login" in driver.current_url.lower():
            logging.error("❌ On login page instead of Stripe!")
            return False

        iframes = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
        )
        if len(iframes) < 3:
            logging.error("❌ Not enough Stripe iframes")
            return False

        driver.switch_to.frame(iframes[0])
        card_field = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cardnumber']"))
        )
        card_field.send_keys(card_number)
        driver.switch_to.default_content()

        driver.switch_to.frame(iframes[1])
        expiry_field = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='exp-date']"))
        )
        expiry_field.send_keys(card_expiry)
        driver.switch_to.default_content()

        driver.switch_to.frame(iframes[2])
        cvc_field = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cvc']"))
        )
        cvc_field.send_keys(card_cvc)
        driver.switch_to.default_content()

        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
        )
        submit_btn.click()

        try:
            WebDriverWait(driver, 20).until(
                lambda d: "confirmation" in d.current_url.lower() or "success" in d.current_url.lower()
            )
            logging.info("🎉 BOOKING CONFIRMED!")
            return True
        except:
            page_source = driver.page_source.lower()
            if any(word in page_source for word in ["confirmed", "success", "booked", "reserved", "confirmation"]):
                logging.info("🎉 BOOKING PROBABLY CONFIRMED!")
                return True
            else:
                logging.error("❌ No confirmation found")
                return False
    except Exception as e:
        logging.error(f"❌ Stripe payment error: {e}")
        return False

# Main execution
try:
    start_time = time.time()
    max_duration = 300

    if not login_first(username, password):
        logging.error("❌ Unable to log in!")
        exit(1)

    booking_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=member"
    driver.get(booking_url)
    time.sleep(2)

    if not check_login_status():
        logging.error("❌ Session lost after navigation!")
        exit(1)

    attempt = 0
    max_attempts = 300

    while attempt < max_attempts and (time.time() - start_time) < max_duration:
        attempt += 1
        if attempt % 10 == 0 and not check_login_status():
            if not login_first(username, password):
                logging.error("❌ Reconnection failed!")
                break
            driver.get(booking_url)
            time.sleep(1)

        logging.info(f"🔄 Attempt {attempt}/{max_attempts} (time: {int(time.time() - start_time)}s)")

        if find_and_book_slot():
            logging.info("🎉 BOOKING SUCCESSFUL!")
            break
        else:
            driver.refresh()
            time.sleep(0.2)

    logging.info(f"✅ Script finished after {int(time.time() - start_time)}s and {attempt} attempts")

except Exception as e:
    logging.error(f"❌ Critical error: {e}")
    if driver:
        take_screenshot("critical_error")
finally:
    if driver:
        driver.quit()
        logging.info("🏁 Driver closed")
