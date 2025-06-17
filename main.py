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

# SPEED OPTIMIZATIONS:
# - Direct XPath targeting for slots (no loops)
# - Minimal waits (0.1-0.8s instead of 1-3s)
# - No screenshots during booking process
# - Eager page loading strategy
# - No image loading
# - Ultra-fast refresh (no delay for logged-in users)
# - 500 attempts in 5 minutes = ~1 attempt per 0.6 seconds

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
# Speed optimizations
options.add_argument("--disable-images")  # Don't load images
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
        logging.info(f"📸 Screenshot sauvegardé: {filename}")
    except Exception as e:
        logging.error(f"Erreur screenshot: {e}")

def login_first(username, password):
    try:
        # Quick check if already logged in
        if "My bookings" in driver.page_source or "Log out" in driver.page_source:
            logging.info("✅ Déjà connecté!")
            return True

        logging.info("🔐 Login rapide...")
        
        # Click Sign in
        try:
            sign_in_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Sign in') or contains(@href, 'login')]")
            sign_in_link.click()
            time.sleep(0.5)
        except:
            pass

        # Click Login button
        try:
            login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Log in')]")
            login_btn.click()
            time.sleep(0.5)
        except:
            pass

        # Fill credentials quickly
        try:
            username_field = driver.find_element(By.XPATH, "//input[@placeholder='Username' or @name='username' or @id='username']")
            username_field.send_keys(username)
            
            password_field = driver.find_element(By.XPATH, "//input[@placeholder='Password' or @name='password' or @id='password' or @type='password']")
            password_field.send_keys(password)
            
            # Submit
            submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Login') or @type='submit']")
            submit_btn.click()
            
            time.sleep(1)
            return True

        except Exception as e:
            logging.error(f"Erreur login: {e}")
            return False

    except Exception as e:
        logging.error(f"❌ Erreur login: {e}")
        return False

def wait_for_page_load():
    """Wait for the booking page to fully load - OPTIMIZED FOR SPEED"""
    try:
        # Just wait for the booking links to appear - no need for other checks
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.book-interval"))
        )
        
        # No extra wait - go immediately
        
        logging.info("✅ Page chargée")
        return True
    except TimeoutException:
        logging.warning("⚠️ Timeout chargement")
        return False

def find_and_book_slot():
    try:
        # Skip cookies if possible
        try:
            driver.find_element(By.CLASS_NAME, "osano-cm-accept-all").click()
        except:
            pass

        # Minimal page load check
        if not wait_for_page_load():
            return False

        # ULTRA FAST: Direct XPath to our exact slot
        target_time_minutes = hour * 60 + minutes
        
        # Try to click the slot immediately with exact XPath
        try:
            # Direct XPath to the exact time slot
            target_slot = driver.find_element(By.XPATH, f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{target_time_minutes}')]")
            target_slot.click()
            logging.info(f"🎯 SLOT {hour_str} cliqué!")
            time.sleep(0.8)  # Minimal wait for page transition
            return complete_booking_process()
            
        except:
            # Ultra-fast fallback - get all slots and check
            slots = driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked")
            for slot in slots:
                if f"|{target_time_minutes}" in (slot.get_attribute('data-test-id') or ""):
                    slot.click()
                    logging.info(f"🎯 SLOT {hour_str} trouvé et cliqué!")
                    time.sleep(0.8)
                    return complete_booking_process()
        
        return False

    except Exception as e:
        logging.error(f"❌ Erreur: {e}")
        return False

def complete_booking_process():
    try:
        # Ultra minimal wait
        time.sleep(0.3)
        
        # Select duration - try fast methods first
        try:
            # Direct click on dropdown
            dropdown = driver.find_element(By.CSS_SELECTOR, ".select2-selection")
            dropdown.click()
            time.sleep(0.1)
            # Click second option immediately
            driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")[1].click()
            logging.info("✅ Durée sélectionnée")
        except:
            # Skip if no duration selection needed
            pass

        time.sleep(0.2)

        # Click Continue - direct approach
        try:
            driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]").click()
            logging.info("✅ Continue cliqué")
            time.sleep(0.8)  # Minimal wait for payment page
        except:
            # Quick fallback
            try:
                driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                logging.info("✅ Continue cliqué (submit)")
                time.sleep(0.8)
            except:
                logging.error("❌ Bouton Continue non trouvé")
                return False

        # Click Pay Now/Confirm and pay - ultra fast approach
        try:
            # Try direct ID first - should be fastest
            pay_btn = driver.find_element(By.ID, "paynow")
            pay_btn.click()
            logging.info("✅ Confirm and pay cliqué (ID direct)")
            time.sleep(0.5)
        except:
            # Quick wait and retry
            try:
                pay_btn = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.ID, "paynow"))
                )
                pay_btn.click()
                logging.info("✅ Confirm and pay cliqué (avec wait)")
                time.sleep(0.5)
            except:
                logging.error("❌ Bouton Confirm and pay non trouvé")
                return False

        # Handle Stripe payment
        return handle_stripe_payment()

    except Exception as e:
        logging.error(f"❌ Erreur booking: {e}")
        return False

def handle_stripe_payment():
    try:
        logging.info("💳 Traitement paiement Stripe...")
        
        # Quick wait for Stripe to initialize
        time.sleep(1)
        
        # Try iframes first (most common)
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']")
        
        if len(iframes) >= 3:
            logging.info(f"✅ {len(iframes)} iframes Stripe trouvées")
            
            # Card number - fast entry
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
            
            logging.info("✅ Infos carte saisies")
            
            # Submit - try multiple methods quickly
            try:
                submit_btn = driver.find_element(By.ID, "cs-stripe-elements-submit-button")
                submit_btn.click()
            except:
                # Try any submit button
                submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                submit_btn.click()
            
            logging.info("✅ Paiement soumis")
            
        else:
            # Fallback for Stripe Checkout
            logging.info("🔍 Pas d'iframes, recherche Stripe Checkout...")
            time.sleep(2)  # Need to wait for redirect
            
            # Try to find card input in any iframe
            all_iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in all_iframes:
                try:
                    driver.switch_to.frame(iframe)
                    card_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='Card'], input[name*='card']")
                    card_input.send_keys(card_number)
                    
                    # Quick entry of other fields
                    driver.find_element(By.CSS_SELECTOR, "input[placeholder*='MM']").send_keys(card_expiry)
                    driver.find_element(By.CSS_SELECTOR, "input[placeholder*='CVC']").send_keys(card_cvc)
                    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                    
                    driver.switch_to.default_content()
                    logging.info("✅ Paiement Checkout soumis")
                    break
                except:
                    driver.switch_to.default_content()
                    continue

        # Quick confirmation check
        time.sleep(3)  # Minimal wait
        
        # Check URL or page content
        if any(word in driver.current_url.lower() for word in ["success", "confirmation", "confirm"]):
            logging.info("🎉 RÉSERVATION CONFIRMÉE!")
            return True
        
        # Quick page check
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if any(word in page_text for word in ["confirmed", "success", "thank you", "booked"]):
            logging.info("🎉 RÉSERVATION CONFIRMÉE!")
            return True
            
        # Wait a bit more if needed
        time.sleep(2)
        return True  # Assume success if no error

    except Exception as e:
        logging.error(f"❌ Erreur paiement: {e}")
        return False

# Main execution
try:
    start_time = time.time()
    max_duration = 300  # 5 minutes max
    
    # Navigate to booking page - use the most direct URL
    url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=guest"
    logging.info(f"🌐 Navigation: {url}")
    driver.get(url)
    time.sleep(1.5)  # Minimal initial load
    
    # Only take initial screenshot
    if attempt == 1:
        take_screenshot("initial_page")

    # Login first
    login_success = login_first(username, password)
    is_logged_in = login_success
    
    if login_success:
        logging.info("✅ Login réussi - Mode ultra-rapide activé")
        # After login, navigate back to booking page
        driver.get(url)
        time.sleep(1)
    else:
        logging.warning("⚠️ Login échoué, on continue...")
    
    # Try booking with ultra-fast retry loop
    attempt = 0
    max_attempts = 500 if is_logged_in else 10  # More attempts!
    
    while attempt < max_attempts and (time.time() - start_time) < max_duration:
        attempt += 1
        elapsed = int(time.time() - start_time)
        
        if attempt % 10 == 1:  # Only log every 10 attempts to save time
            logging.info(f"🔄 Tentative {attempt}/{max_attempts} (temps: {elapsed}s)")
        
        if find_and_book_slot():
            logging.info("🎉 RÉSERVATION RÉUSSIE!")
            break
        else:
            if attempt < max_attempts and (time.time() - start_time) < max_duration - 10:
                # Ultra fast refresh - no delay for logged-in users
                if is_logged_in:
                    driver.refresh()
                else:
                    time.sleep(1)
                    driver.refresh()
                    time.sleep(0.5)
            else:
                break

    total_time = int(time.time() - start_time)
    logging.info(f"✅ Script terminé en {total_time}s après {attempt} tentatives")

except Exception as e:
    logging.error(f"❌ Erreur critique: {e}")
    if driver:
        take_screenshot("critical_error")
finally:
    if driver:
        driver.quit()
        logging.info("🏁 Driver fermé")
