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
from concurrent.futures import ThreadPoolExecutor
import threading

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking.log'),
        logging.StreamHandler()
    ]
)

# Configuration Chrome - Optimized for speed
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
# Performance optimizations
options.add_argument("--disable-images")
options.add_argument("--disable-javascript")  # Will re-enable after login
options.page_load_strategy = 'eager'  # Don't wait for all resources

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

# Initialize driver - GLOBAL VARIABLE
driver = None

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_size(1920, 1080)
    driver.implicitly_wait(1)  # Reduce implicit wait
    logging.info("✅ Driver initialisé")
except Exception as e:
    logging.error(f"❌ Erreur driver: {e}")
    exit(1)

def take_screenshot(name):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{name}_{timestamp}.png"
        driver.save_screenshot(filename)
        logging.info(f"📸 Screenshot sauvegardé: {filename}")
    except Exception as e:
        logging.error(f"Erreur screenshot: {e}")

def check_login_status():
    """Ultra-fast login check"""
    try:
        # Quick check without waiting
        indicators = driver.find_elements(By.XPATH, "//*[contains(text(), 'Log out') or contains(text(), 'My bookings')]")
        return len(indicators) > 0
    except:
        return False

def login_first(username, password):
    try:
        logging.info("🔐 Login ultra-rapide...")
        
        # Re-enable JavaScript for login
        driver.execute_cdp_cmd('Emulation.setScriptExecutionDisabled', {'value': False})
        
        # Direct navigation to login
        driver.get("https://clubspark.lta.org.uk/SouthwarkPark")
        time.sleep(1.5)
        
        # Quick cookie acceptance
        try:
            driver.find_element(By.CLASS_NAME, "osano-cm-accept-all").click()
        except:
            pass

        # Fast login sequence
        try:
            sign_in = driver.find_element(By.XPATH, "//a[contains(@href, 'login') or contains(text(), 'Sign in')]")
            sign_in.click()
            time.sleep(1)
        except:
            driver.get("https://clubspark.lta.org.uk/SouthwarkPark/Account/Login")
            time.sleep(1)

        # Try login button
        try:
            driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]").click()
            time.sleep(0.5)
        except:
            pass

        # Fill credentials immediately
        username_field = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//input[@name='username' or @id='username' or @placeholder='Username']"))
        )
        username_field.send_keys(username)
        
        password_field = driver.find_element(By.XPATH, "//input[@type='password']")
        password_field.send_keys(password)
        
        # Submit
        submit_btn = driver.find_element(By.XPATH, "//button[@type='submit' or contains(text(), 'Log in')]")
        submit_btn.click()
        
        time.sleep(2)
        
        if check_login_status():
            logging.info("✅ Login confirmé!")
            return True
        else:
            logging.error("❌ Login échoué")
            return False

    except Exception as e:
        logging.error(f"❌ Erreur login: {e}")
        return False

def ultra_fast_slot_finder():
    """Find slot without waiting for full page load"""
    try:
        target_time_minutes = hour * 60 + minutes
        xpath_query = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{target_time_minutes}')]"
        
        # Don't wait for page load, just look for the slot
        try:
            target_slot = driver.find_element(By.XPATH, xpath_query)
            if target_slot:
                logging.info(f"⚡ SLOT TROUVÉ INSTANTANÉMENT à {hour_str}!")
                target_slot.click()
                return True
        except:
            pass
        
        # Quick fallback - all slots
        slots = driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked")
        for slot in slots:
            data_test_id = slot.get_attribute('data-test-id') or ""
            if f"|{target_time_minutes}" in data_test_id:
                logging.info(f"⚡ SLOT TROUVÉ à {hour_str}!")
                slot.click()
                return True
        
        return False
    except:
        return False

def complete_booking_ultra_fast():
    """Complete booking at maximum speed"""
    try:
        time.sleep(0.8)  # Minimal wait
        
        # Ultra-fast duration selection
        try:
            # Try select2 first
            driver.find_element(By.CSS_SELECTOR, ".select2-selection").click()
            time.sleep(0.1)
            options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
            if len(options) >= 2:
                options[1].click()
        except:
            # Fallback to regular select
            try:
                Select(driver.find_element(By.ID, "booking-duration")).select_by_index(1)
            except:
                pass
        
        time.sleep(0.2)
        
        # Click Continue immediately
        try:
            driver.find_element(By.XPATH, "//button[contains(text(), 'Continue') or @type='submit']").click()
        except:
            return False
        
        time.sleep(1.5)  # Critical wait for page transition
        
        # Check if redirected to login
        if "login" in driver.current_url.lower():
            logging.error("❌ Session perdue!")
            return False
        
        # Click payment button with multiple strategies simultaneously
        payment_clicked = False
        
        # Strategy 1: Direct ID
        try:
            pay_btn = driver.find_element(By.ID, "paynow")
            driver.execute_script("arguments[0].click();", pay_btn)
            payment_clicked = True
        except:
            pass
        
        # Strategy 2: Any button with payment attributes
        if not payment_clicked:
            try:
                pay_btn = driver.find_element(By.CSS_SELECTOR, "button[data-stripe-payment='true']")
                driver.execute_script("arguments[0].click();", pay_btn)
                payment_clicked = True
            except:
                pass
        
        if not payment_clicked:
            logging.error("❌ Bouton payment non trouvé")
            return False
        
        logging.info("✅ Payment initié")
        time.sleep(1.5)
        
        # Ultra-fast Stripe handling
        return handle_stripe_ultra_fast()
        
    except Exception as e:
        logging.error(f"❌ Erreur booking: {e}")
        return False

def handle_stripe_ultra_fast():
    """Handle Stripe payment at maximum speed"""
    try:
        # Wait for iframes
        iframes = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
        )
        
        if len(iframes) < 3:
            return False
        
        # Fill all fields as fast as possible
        # Card number
        driver.switch_to.frame(iframes[0])
        card_field = driver.find_element(By.CSS_SELECTOR, "input")
        card_field.send_keys(card_number)
        driver.switch_to.default_content()
        
        # Expiry
        driver.switch_to.frame(iframes[1])
        expiry_field = driver.find_element(By.CSS_SELECTOR, "input")
        expiry_field.send_keys(card_expiry)
        driver.switch_to.default_content()
        
        # CVC
        driver.switch_to.frame(iframes[2])
        cvc_field = driver.find_element(By.CSS_SELECTOR, "input")
        cvc_field.send_keys(card_cvc)
        driver.switch_to.default_content()
        
        # Submit immediately
        submit_btn = driver.find_element(By.ID, "cs-stripe-elements-submit-button")
        driver.execute_script("arguments[0].click();", submit_btn)
        
        logging.info("✅ Paiement soumis")
        
        # Wait for confirmation
        time.sleep(5)
        if any(word in driver.page_source.lower() for word in ["confirmed", "success", "booked"]):
            logging.info("🎉 RÉSERVATION CONFIRMÉE!")
            take_screenshot("confirmation")
            return True
        
        return False
        
    except Exception as e:
        logging.error(f"❌ Erreur Stripe: {e}")
        return False

# Main execution - ULTRA FAST MODE
try:
    start_time = time.time()
    
    # Login phase
    if not login_first(username, password):
        logging.error("❌ Login impossible!")
        exit(1)
    
    # Navigate to booking page
    booking_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=member"
    driver.get(booking_url)
    
    # Don't wait for full page load - start checking immediately
    time.sleep(1)
    
    # Ultra-fast booking loop
    attempt = 0
    max_attempts = 500  # More attempts since they're faster
    success = False
    
    while attempt < max_attempts and (time.time() - start_time) < 300:
        attempt += 1
        
        # Skip the "page loaded" check - go straight to finding slots
        if ultra_fast_slot_finder():
            if complete_booking_ultra_fast():
                success = True
                break
        
        # Ultra-fast refresh - no delay
        if attempt % 2 == 0:  # Refresh every 2 attempts to avoid rate limiting
            driver.refresh()
        
        # Log progress every 10 attempts
        if attempt % 10 == 0:
            elapsed = int(time.time() - start_time)
            logging.info(f"⚡ {attempt} tentatives en {elapsed}s")
    
    total_time = int(time.time() - start_time)
    if success:
        logging.info(f"🎉 RÉSERVATION RÉUSSIE en {total_time}s après {attempt} tentatives!")
    else:
        logging.info(f"❌ Échec après {total_time}s et {attempt} tentatives")

except Exception as e:
    logging.error(f"❌ Erreur critique: {e}")
    take_screenshot("critical_error")
finally:
    if driver:
        driver.quit()
        logging.info("🏁 Fin du script")
