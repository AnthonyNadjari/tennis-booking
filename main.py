import os
import time
import logging
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='[%(process)d] %(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'booking_{os.getpid()}.log'),
        logging.StreamHandler()
    ]
)

# User-agent pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/126.0",
    "Mozilla/5.0 (Linux; Android 14; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
]

def get_chrome_options():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # Randomize user-agent
    ua = random.choice(USER_AGENTS)
    options.add_argument(f"user-agent={ua}")
    return options

def take_screenshot(driver, name):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{name}_{os.getpid()}_{timestamp}.png"
        driver.save_screenshot(filename)
        logging.info(f"📸 Screenshot saved: {filename}")
    except Exception as e:
        logging.error(f"Screenshot error: {e}")

def login_first(driver, username, password):
    try:
        # Check if already logged in
        page = driver.page_source
        if "My bookings" in page or "Log out" in page:
            logging.info("✅ Already logged in!")
            return True

        logging.info("🔐 Attempting login...")

        # Try to find any sign in link or button
        sign_in = None
        for xpath in [
            "//a[contains(text(), 'Sign in') or contains(@href, 'login')]",
            "//button[contains(text(), 'Sign in')]"
        ]:
            try:
                sign_in = WebDriverWait(driver, 6).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                sign_in.click()
                logging.info("✅ Clicked Sign in")
                time.sleep(1)
                break
            except Exception:
                continue

        # Wait for login fields to be visible
        try:
            username_field = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//input[contains(@placeholder, 'Username') or @name='username' or @id='username']"
                ))
            )
            logging.info("✅ Username field appeared")
        except Exception as e:
            logging.error("❌ Username field not found!")
            take_screenshot(driver, "login_no_username")
            # Dump form HTML for debug
            html = driver.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")
            logging.error("Login area HTML snippet:\n" + html[:2000])
            return False

        # Find password field
        try:
            password_field = driver.find_element(
                By.XPATH,
                "//input[contains(@placeholder, 'Password') or @name='password' or @id='password' or @type='password']"
            )
        except Exception as e:
            logging.error("❌ Password field not found!")
            take_screenshot(driver, "login_no_password")
            html = driver.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")
            logging.error("Login area HTML snippet:\n" + html[:2000])
            return False

        # Enter credentials and submit
        try:
            username_field.clear()
            username_field.send_keys(username)
            password_field.clear()
            password_field.send_keys(password)
            logging.info("✅ Entered credentials")

            # Find and click submit
            submit_btn = None
            for xpath in [
                "//button[contains(text(), 'Log in')]",
                "//button[contains(text(), 'Login')]",
                "//button[@type='submit']"
            ]:
                try:
                    submit_btn = driver.find_element(By.XPATH, xpath)
                    break
                except Exception:
                    continue
            if submit_btn:
                submit_btn.click()
                logging.info("✅ Clicked Login button.")
            else:
                logging.error("❌ Login/submit button not found!")
                take_screenshot(driver, "login_no_submit")
                return False

            # Wait to be logged in or see error
            time.sleep(2)
            page_res = driver.page_source
            if "My bookings" in page_res or "Log out" in page_res:
                logging.info("✅ Successfully logged in!")
                return True
            elif "incorrect" in page_res.lower() or "invalid" in page_res.lower():
                logging.error("❌ Login failed: Credentials incorrect?")
                take_screenshot(driver, "login_bad_creds")
                return False
            else:
                logging.warning("⚠️ Login may have failed (no confirmation text found).")
                take_screenshot(driver, "login_unclear")
                return False

        except Exception as e:
            logging.error(f"❌ Error during credential entry or submit: {e}")
            take_screenshot(driver, "login_submit_error")
            return False

    except Exception as e:
        logging.error(f"❌ Unhandled login error: {e}")
        take_screenshot(driver, "login_unhandled")
        return False
def wait_for_page_load(driver):
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.book-interval"))
        )
        return True
    except TimeoutException:
        logging.warning("⚠️ Timeout loading page")
        return False

def find_and_book_slot_all_courts(driver, total_minutes, hour_str, court_filter=None):
    try:
        # Accept cookies first - but don't wait if not there
        try:
            cookie_btn = driver.find_element(By.CLASS_NAME, "osano-cm-accept-all")
            cookie_btn.click()
            time.sleep(0.1)
        except:
            pass

        if not wait_for_page_load(driver):
            return False

        logging.info(f"🔍 Searching slots at {hour_str}...")

        # Filter for a specific court if court_filter is set (e.g. "Court 2")
        if court_filter:
            xpath_query = f"//a[contains(@class,'book-interval') and contains(@class,'not-booked') and contains(@data-test-id, '|{total_minutes}') and contains(@data-test-id, '{court_filter}') and not(contains(@class, 'disabled'))]"
        else:
            xpath_query = f"//a[contains(@class,'book-interval') and contains(@class,'not-booked') and contains(@data-test-id, '|{total_minutes}') and not(contains(@class, 'disabled'))]"

        slots = driver.find_elements(By.XPATH, xpath_query)

        if slots:
            for slot in slots:
                try:
                    logging.info("🎯 SLOT AVAILABLE, trying to book...")
                    slot.click()
                    if complete_booking_process(driver):
                        return True
                except ElementClickInterceptedException:
                    logging.warning("⚠️ Slot click intercepted, trying next.")
                    continue

        logging.debug(f"No slot found for {hour_str} (court_filter={court_filter})")
        return False

    except Exception as e:
        logging.error(f"❌ Slot search error: {e}")
        return False

def complete_booking_process(driver):
    try:
        # Try to select duration
        try:
            duration_select = driver.find_element(By.ID, "booking-duration")
            Select(duration_select).select_by_index(1)
            logging.info("✅ Duration selected (booking-duration)")
        except:
            try:
                select2_dropdown = driver.find_element(By.CSS_SELECTOR, ".select2-selection, .select2-selection--single")
                select2_dropdown.click()
                options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
                if len(options) >= 2:
                    options[1].click()
                    logging.info("✅ Duration selected (select2)")
            except:
                pass

        try:
            continue_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
            continue_btn.click()
        except:
            try:
                continue_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
                continue_btn.click()
            except:
                logging.error("❌ Continue button not found")
                return False

        try:
            pay_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, "paynow"))
            )
            pay_btn.click()
        except:
            logging.error("❌ Pay Now button not found")
            return False

        return handle_stripe_payment(driver)

    except Exception as e:
        logging.error(f"❌ Booking process error: {e}")
        return False

def handle_stripe_payment(driver):
    try:
        logging.info("💳 Stripe payment...")
        iframes = WebDriverWait(driver, 12).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
        )
        if len(iframes) < 3:
            logging.error("❌ Not enough Stripe iframes")
            return False

        # Card number
        driver.switch_to.frame(iframes[0])
        card_field = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cardnumber'], input[placeholder*='card'], input[data-elements-stable-field-name='cardNumber']"))
        )
        card_field.clear()
        card_field.send_keys(os.environ.get('CARD_NUMBER', '5555555555554444'))
        driver.switch_to.default_content()

        # Expiry date
        driver.switch_to.frame(iframes[1])
        expiry_field = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='exp-date'], input[placeholder*='MM'], input[data-elements-stable-field-name='cardExpiry']"))
        )
        expiry_field.clear()
        expiry_field.send_keys(os.environ.get('CARD_EXPIRY', '04/30'))
        driver.switch_to.default_content()

        # CVC
        driver.switch_to.frame(iframes[2])
        cvc_field = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cvc'], input[placeholder*='CVC'], input[data-elements-stable-field-name='cardCvc']"))
        )
        cvc_field.clear()
        cvc_field.send_keys(os.environ.get('CARD_CVC', '666'))
        driver.switch_to.default_content()

        # Submit payment
        submit_btn = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        submit_btn.click()

        try:
            WebDriverWait(driver, 14).until(
                lambda d: "confirmation" in d.current_url.lower() or "success" in d.current_url.lower()
            )
            logging.info("🎉 BOOKING CONFIRMED!")
            return True
        except:
            time.sleep(3)
            page_source = driver.page_source.lower()
            if any(word in page_source for word in ["confirmed", "success", "booked", "reserved", "confirmation"]):
                logging.info("🎉 BOOKING PROBABLY CONFIRMED!")
                return True
            else:
                logging.error("❌ No confirmation found")
                return False

    except Exception as e:
        logging.error(f"❌ Stripe payment error: {e}")
        take_screenshot(driver, "stripe_error")
        return False

def main():
    # Print a warning if not using NTP for true clock sync
    try:
        import ntplib
        logging.info("System NTP sync recommended for lowest latency!")
    except ImportError:
        logging.warning("ntplib not installed. Ensure your system clock is NTP-synced for best performance!")

    # Environment Variables
    account_number = os.environ.get('ACCOUNT', '1')
    username = os.environ.get('TENNIS_USERNAME2') if account_number == '2' else os.environ.get('TENNIS_USERNAME')
    password = os.environ.get('TENNIS_PASSWORD')
    date = os.environ.get('BOOKING_DATE', '2025-06-16')
    hour = int(os.environ.get('BOOKING_HOUR', '7'))
    minutes = int(os.environ.get('BOOKING_MINUTES', '0'))
    total_minutes = (hour * 60) + minutes
    hour_str = f"{hour:02d}:{minutes:02d}"
    court_filter = os.environ.get('COURT_FILTER', None)

    base_urls = [
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=guest",
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate?date={date}",
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/Calendar?date={date}",
        "https://clubspark.lta.org.uk/SouthwarkPark/Booking"
    ]

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=get_chrome_options())
        driver.set_window_size(1920, 1080)
        url_success = False
        for url in base_urls:
            try:
                driver.get(url)
                time.sleep(1)
                if "booking" in driver.current_url.lower() or "calendar" in driver.current_url.lower():
                    url_success = True
                    break
            except:
                continue
        if not url_success:
            logging.error("❌ Could not reach booking page")
            return

        if not login_first(driver, username, password):
            logging.error("❌ Login failed")
            return
        driver.get(base_urls[0])
        time.sleep(1)

        # Main booking loop
        start_time = time.time()
        max_duration = int(os.environ.get("MAX_DURATION", "1800"))  # seconds
        attempt = 0
        while True:
            attempt += 1
            elapsed = int(time.time() - start_time)
            logging.info(f"🔄 Attempt {attempt} (elapsed: {elapsed}s)")
            if find_and_book_slot_all_courts(driver, total_minutes, hour_str, court_filter):
                logging.info("🎉 RESERVATION SUCCESSFUL (exit loop)")
                break
            if max_duration and elapsed > max_duration:
                logging.warning("⏳ Max duration reached, stopping.")
                break
            # No fixed sleep, just a micro-random delay to avoid spamming too hard
            time.sleep(random.uniform(0.05, 0.25))
            driver.refresh()

    except Exception as e:
        logging.error(f"❌ Critical error: {e}")
        take_screenshot(driver, "critical_error")
    finally:
        if driver:
            driver.quit()
            logging.info("🏁 Driver closed")

if __name__ == "__main__":
    main()
