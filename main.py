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
import re

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking.log'),
        logging.StreamHandler()
    ]
)

# Configuration Chrome
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

# Variables d'environnement
account_number = os.environ.get('ACCOUNT', '1')
if account_number == '2':
    username = os.environ.get('TENNIS_USERNAME2')
    logging.info("🔑 Utilisation du compte secondaire (TENNIS_USERNAME2)")
else:
    username = os.environ.get('TENNIS_USERNAME')
    logging.info("🔑 Utilisation du compte principal (TENNIS_USERNAME)")

password = os.environ.get('TENNIS_PASSWORD')
card_number = os.environ.get('CARD_NUMBER', '5354562794845156')
card_expiry = os.environ.get('CARD_EXPIRY', '04/30')
card_cvc = os.environ.get('CARD_CVC', '666')
date = os.environ.get('BOOKING_DATE', '2025-06-16')
hour = int(os.environ.get('BOOKING_HOUR', '7'))
minutes = int(os.environ.get('BOOKING_MINUTES', '0'))

if not username or not password:
    logging.error("❌ Username ou password non définis!")
    exit(1)

# Calculate total minutes and format display
total_minutes = (hour * 60) + minutes
hour_system_minutes = total_minutes
hour_str = f"{hour:02d}:{minutes:02d}"

logging.info(f"🎾 Réservation pour le {date} à {hour_str}")
logging.info(f"⏰ Minutes système: {hour_system_minutes}")
logging.info(f"👤 Compte: {account_number} ({'Principal' if account_number == '1' else 'Secondaire'})")
logging.info(f"📸 Les screenshots seront sauvegardés dans le répertoire courant")

# Initialize driver - GLOBAL VARIABLE
driver = None

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_size(1920, 1080)
    logging.info("✅ Driver initialisé")
except Exception as e:
    logging.error(f"❌ Erreur driver: {e}")
    exit(1)

def take_screenshot(name):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{name}_{timestamp}.png"
        driver.save_screenshot(filename)
        logging.info(f"📸 Screenshot saved: {filename}")
        return filename
    except Exception as e:
        logging.error(f"Screenshot error: {e}")
        return None

def log_page_source(description):
    try:
        page_source = driver.page_source
        # Write to a file for easier inspection
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"page_source_{description}_{timestamp}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(page_source)
        logging.info(f"📄 Page source saved: {filename}")
        return filename
    except Exception as e:
        logging.error(f"Error saving page source: {e}")
        return None

def complete_booking_process():
    try:
        # Initial wait
        time.sleep(0.5)
        take_screenshot("start_booking_process")
        log_page_source("start_booking_process")

        # Select duration quickly
        try:
            take_screenshot("before_duration_selection")
            log_page_source("before_duration_selection")

            select2_dropdown = driver.find_element(By.CSS_SELECTOR, ".select2-selection, .select2-selection--single")
            select2_dropdown.click()
            time.sleep(0.1)

            options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
            if len(options) >= 2:
                options[1].click()
                logging.info("✅ Duration selected")
                time.sleep(0.2)
                take_screenshot("after_duration_selection")
                log_page_source("after_duration_selection")
        except Exception as e:
            logging.warning(f"Duration selection error: {e}")
            try:
                duration_select = driver.find_element(By.ID, "booking-duration")
                Select(duration_select).select_by_index(1)
                logging.info("✅ Duration selected (alternative method)")
                time.sleep(0.2)
                take_screenshot("after_duration_selection_alt")
                log_page_source("after_duration_selection_alt")
            except Exception as e2:
                logging.error(f"❌ Could not select duration: {e2}")
                take_screenshot("duration_selection_failed")
                log_page_source("duration_selection_failed")
                return False

        # Click Continue
        try:
            take_screenshot("before_continue")
            log_page_source("before_continue")

            continue_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]"))
            )
            continue_btn.click()
            logging.info("✅ Continue button clicked")
            time.sleep(1)
            take_screenshot("after_continue")
            log_page_source("after_continue")
        except Exception as e:
            logging.warning(f"Continue button not found (first attempt): {e}")
            try:
                continue_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
                continue_btn.click()
                logging.info("✅ Continue button clicked (alternative method)")
                time.sleep(1)
                take_screenshot("after_continue_alt")
                log_page_source("after_continue_alt")
            except Exception as e2:
                logging.error(f"❌ Could not find Continue button: {e2}")
                take_screenshot("continue_button_failed")
                log_page_source("continue_button_failed")
                return False

        # Click Pay Now - enhanced approach with multiple fallback methods
        try:
            logging.info("Searching for Pay Now button...")
            take_screenshot("before_pay_button")
            log_page_source("before_pay_button")

            # Try multiple strategies with a longer timeout (15 seconds)
            pay_btn = None

            # Strategy 1: Try by ID (paynow)
            try:
                pay_btn = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.ID, "paynow"))
                )
                logging.info("Pay Now button found by ID")
            except:
                pass

            # Strategy 2: Try by text "Confirm and pay"
            if not pay_btn:
                try:
                    pay_btn = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Confirm and pay')]"))
                    )
                    logging.info("Pay Now button found by text 'Confirm and pay'")
                except:
                    pass

            # Strategy 3: Try by Stripe payment attribute
            if not pay_btn:
                try:
                    pay_btn = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(@data-stripe-payment, 'true')]"))
                    )
                    logging.info("Pay Now button found by Stripe attribute")
                except:
                    pass

            # Strategy 4: Try by looking for any button that looks like a payment button
            if not pay_btn:
                try:
                    buttons = driver.find_elements(By.XPATH, "//button")
                    for button in buttons:
                        button_text = button.text.lower()
                        if "pay" in button_text or "confirm" in button_text or "checkout" in button_text:
                            pay_btn = button
                            break
                    if pay_btn:
                        logging.info("Pay Now button found by text search")
                except:
                    pass

            if pay_btn:
                try:
                    # Try normal click first
                    pay_btn.click()
                    logging.info("✅ Pay Now button clicked (normal method)")
                except Exception as click_error:
                    try:
                        # If normal click fails, try JavaScript click
                        driver.execute_script("arguments[0].click();", pay_btn)
                        logging.info("✅ Pay Now button clicked (JavaScript method)")
                    except Exception as js_click_error:
                        logging.error(f"❌ Could not click Pay Now button: {js_click_error}")
                        take_screenshot("pay_button_click_failed")
                        log_page_source("pay_button_click_failed")
                        return False
                time.sleep(1)
                take_screenshot("after_pay_button")
                log_page_source("after_pay_button")
            else:
                logging.error("❌ Pay Now button not found after all attempts")
                take_screenshot("pay_button_not_found")
                log_page_source("pay_button_not_found")
                return False

        except Exception as e:
            logging.error(f"❌ Error finding/clicking Pay Now button: {e}")
            take_screenshot("pay_button_error")
            log_page_source("pay_button_error")
            return False

        # Handle Stripe payment
        return handle_stripe_payment()

    except Exception as e:
        logging.error(f"❌ Error in complete_booking_process: {e}")
        take_screenshot("booking_process_failed")
        log_page_source("booking_process_failed")
        return False

def handle_stripe_payment():
    try:
        logging.info("💳 Processing Stripe payment...")
        take_screenshot("stripe_form_start")
        log_page_source("stripe_form_start")

        # Wait for Stripe iframes to load
        iframes = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
        )
        logging.info(f"✅ Found {len(iframes)} Stripe iframes")

        if len(iframes) < 3:
            logging.error("❌ Not enough Stripe iframes found")
            take_screenshot("stripe_iframe_error")
            log_page_source("stripe_iframe_error")
            return False

        # Card number
        driver.switch_to.frame(iframes[0])
        take_screenshot("card_number_frame")
        card_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cardnumber'], input[placeholder*='card'], input[data-elements-stable-field-name='cardNumber']"))
        )
        card_field.clear()
        card_field.send_keys(card_number)
        driver.switch_to.default_content()
        logging.info("✅ Card number entered")
        time.sleep(0.2)

        # Expiry date
        driver.switch_to.frame(iframes[1])
        take_screenshot("card_expiry_frame")
        expiry_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='exp-date'], input[placeholder*='MM'], input[data-elements-stable-field-name='cardExpiry']"))
        )
        expiry_field.clear()
        expiry_field.send_keys(card_expiry)
        driver.switch_to.default_content()
        logging.info("✅ Expiry date entered")
        time.sleep(0.2)

        # CVC
        driver.switch_to.frame(iframes[2])
        take_screenshot("card_cvc_frame")
        cvc_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cvc'], input[placeholder*='CVC'], input[data-elements-stable-field-name='cardCvc']"))
        )
        cvc_field.clear()
        cvc_field.send_keys(card_cvc)
        driver.switch_to.default_content()
        logging.info("✅ CVC entered")
        time.sleep(0.2)

        # Submit payment
        take_screenshot("before_payment_submit")
        log_page_source("before_payment_submit")

        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(0.5)
        submit_btn.click()
        logging.info("✅ Payment submitted")
        time.sleep(1)
        take_screenshot("after_payment_submit")
        log_page_source("after_payment_submit")

        # Wait for confirmation
        try:
            WebDriverWait(driver, 30).until(
                lambda d: "confirmation" in d.current_url.lower() or "success" in d.current_url.lower()
            )
            take_screenshot("confirmation_page")
            log_page_source("confirmation_page")
            logging.info("🎉 BOOKING CONFIRMED!")
            return True
        except:
            # Check for any success indicators on page
            time.sleep(5)
            page_source = driver.page_source.lower()
            take_screenshot("possible_success_page")
            log_page_source("possible_success_page")

            if any(word in page_source for word in ["confirmed", "success", "booked", "reserved", "confirmation"]):
                logging.info("🎉 BOOKING LIKELY CONFIRMED!")
                return True
            else:
                logging.error("❌ No confirmation found")
                return False

    except Exception as e:
        logging.error(f"❌ Stripe payment error: {e}")
        take_screenshot("stripe_payment_error")
        log_page_source("stripe_payment_error")
        return False
