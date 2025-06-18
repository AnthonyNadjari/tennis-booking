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
    """Check if we're currently logged in"""
    try:
        page_source = driver.page_source
        # Multiple indicators of being logged in
        logged_in_indicators = ["My bookings", "Log out", "Sign out", "My account", "Account settings"]
        
        for indicator in logged_in_indicators:
            if indicator in page_source:
                return True
        
        # Check for login form as negative indicator
        if "username" in page_source.lower() and "password" in page_source.lower():
            if "login" in driver.current_url.lower() or "signin" in driver.current_url.lower():
                return False
        
        return False
    except:
        return False

def login_first(username, password):
    try:
        logging.info("🔐 Processus de connexion complet...")
        
        # Navigate to main page first
        driver.get("https://clubspark.lta.org.uk/SouthwarkPark")
        time.sleep(2)
        
        # Accept cookies if present
        try:
            cookie_btn = driver.find_element(By.CLASS_NAME, "osano-cm-accept-all")
            cookie_btn.click()
            time.sleep(0.5)
        except:
            pass

        # Step 1: Click Sign in
        try:
            sign_in_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in') or contains(@href, 'login')]"))
            )
            sign_in_link.click()
            logging.info("✅ Cliqué sur Sign in")
            time.sleep(2)
        except Exception as e:
            logging.warning(f"Sign in non trouvé: {e}")
            # Try direct navigation to login
            driver.get("https://clubspark.lta.org.uk/SouthwarkPark/Account/Login")
            time.sleep(2)

        # Step 2: Click Login button if needed
        try:
            login_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Log in')]"))
            )
            login_btn.click()
            logging.info("✅ Cliqué sur Login")
            time.sleep(2)
        except:
            pass

        # Step 3: Fill credentials
        try:
            # Wait for form to be present
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Username' or @name='username' or @id='username']"))
            )
            
            username_field = driver.find_element(By.XPATH, "//input[@placeholder='Username' or @name='username' or @id='username']")
            username_field.clear()
            username_field.send_keys(username)
            logging.info("✅ Username saisi")

            password_field = driver.find_element(By.XPATH, "//input[@placeholder='Password' or @name='password' or @id='password' or @type='password']")
            password_field.clear()
            password_field.send_keys(password)
            logging.info("✅ Password saisi")

            # Submit login
            submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Login') or @type='submit']")
            submit_btn.click()
            logging.info("✅ Login soumis")

            # Wait for login to complete
            time.sleep(3)
            
            # Verify login succeeded
            if check_login_status():
                logging.info("✅ Login confirmé!")
                # Save cookies
                cookies = driver.get_cookies()
                logging.info(f"🍪 {len(cookies)} cookies sauvegardés")
                return True
            else:
                logging.error("❌ Login non confirmé")
                take_screenshot("login_failed")
                return False

        except Exception as e:
            logging.error(f"Erreur saisie credentials: {e}")
            take_screenshot("login_error")
            return False

    except Exception as e:
        logging.error(f"❌ Erreur login: {e}")
        take_screenshot("login_error")
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
                logging.info(f"🎯 SLOT TROUVÉ DIRECTEMENT à {hour_str}!")
                target_slot.click()
                logging.info("✅ Cliqué!")
                return True
        except:
            pass
        
        # Quick fallback - all slots
        slots = driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked")
        for slot in slots:
            data_test_id = slot.get_attribute('data-test-id') or ""
            if f"|{target_time_minutes}" in data_test_id:
                logging.info(f"🎯 SLOT TROUVÉ à {hour_str}!")
                slot.click()
                logging.info("✅ Cliqué!")
                return True
        
        return False
    except:
        return False

def complete_booking_ultra_fast():
    """Complete booking at maximum speed"""
    try:
        time.sleep(1)  # Slightly longer initial wait
        
        # CRITICAL: Check we're still logged in after clicking slot
        current_url = driver.current_url
        logging.info(f"📍 URL après clic slot: {current_url}")
        
        if "login" in current_url.lower() or not check_login_status():
            logging.error("❌ Redirigé vers login après sélection du slot!")
            take_screenshot("redirected_to_login")
            return False
        
        # Ultra-fast duration selection
        try:
            # Try select2 first
            driver.find_element(By.CSS_SELECTOR, ".select2-selection").click()
            time.sleep(0.2)
            options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
            if len(options) >= 2:
                options[1].click()
                logging.info("✅ Durée sélectionnée")
        except:
            # Fallback to regular select
            try:
                Select(driver.find_element(By.ID, "booking-duration")).select_by_index(1)
                logging.info("✅ Durée sélectionnée")
            except:
                pass
        
        time.sleep(0.3)
        
        # Click Continue immediately
        try:
            driver.find_element(By.XPATH, "//button[contains(text(), 'Continue') or @type='submit']").click()
            logging.info("✅ Continue cliqué")
        except:
            logging.error("❌ Bouton Continue non trouvé")
            return False
        
        time.sleep(2)  # Critical wait for page transition
        
        # CRITICAL: Check again after Continue
        current_url = driver.current_url
        logging.info(f"📍 URL après Continue: {current_url}")
        
        if "login" in current_url.lower():
            logging.error("❌ Redirigé vers login après Continue!")
            take_screenshot("login_redirect_after_continue")
            return False
        
        # Click payment button with multiple strategies
        payment_clicked = False
        
        # Wait a bit for the button to appear
        time.sleep(0.5)
        
        # Strategy 1: Direct ID with wait
        try:
            pay_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "paynow"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pay_btn)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", pay_btn)
            payment_clicked = True
            logging.info("✅ Confirm and pay cliqué")
        except:
            pass
        
        # Strategy 2: Any button with payment attributes
        if not payment_clicked:
            try:
                pay_btn = driver.find_element(By.CSS_SELECTOR, "button[data-stripe-payment='true']")
                driver.execute_script("arguments[0].click();", pay_btn)
                payment_clicked = True
                logging.info("✅ Confirm and pay cliqué (data-stripe)")
            except:
                pass
        
        if not payment_clicked:
            logging.error("❌ Bouton payment non trouvé")
            take_screenshot("payment_button_not_found")
            return False
        
        time.sleep(2)
        
        # Ultra-fast Stripe handling
        return handle_stripe_ultra_fast()
        
    except Exception as e:
        logging.error(f"❌ Erreur booking: {e}")
        take_screenshot("booking_error")
        return False

def handle_stripe_ultra_fast():
    """Handle Stripe payment at maximum speed"""
    try:
        logging.info("💳 Traitement paiement Stripe...")
        
        # Check one more time we're not on login page
        if "login" in driver.current_url.lower():
            logging.error("❌ Sur la page de login au lieu de Stripe!")
            return False
        
        # Wait a bit for the Stripe modal to fully appear
        time.sleep(1)
        
        take_screenshot("stripe_form")
        
        # Look for the Stripe modal/popup first
        try:
            # Check if there's a Stripe modal visible
            stripe_modal = driver.find_element(By.CSS_SELECTOR, ".StripeElement, [class*='stripe'], #stripe-modal, .payment-modal")
            logging.info("✅ Modal Stripe détecté")
        except:
            logging.info("⚠️ Pas de modal Stripe détecté, continuation...")
        
        # Wait for iframes with better error handling
        try:
            iframes = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
            )
            logging.info(f"✅ {len(iframes)} iframes Stripe trouvées")
        except TimeoutException:
            logging.error("❌ Timeout en attendant les iframes Stripe")
            # Try alternative iframe selectors
            iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='stripe'], iframe[title*='Secure']")
            if not iframes:
                return False
        
        if len(iframes) < 3:
            logging.error(f"❌ Seulement {len(iframes)} iframes Stripe trouvées (3 attendues)")
            # Log iframe details for debugging
            for i, iframe in enumerate(iframes):
                name = iframe.get_attribute('name')
                src = iframe.get_attribute('src')
                logging.debug(f"Iframe {i}: name={name}, src={src[:50]}...")
            return False
        
        # Wait for iframes to be ready
        time.sleep(1)
        
        # Fill all fields with proper waits for interactability
        try:
            # Card number
            driver.switch_to.frame(iframes[0])
            card_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='cardnumber'], input[placeholder*='card'], input[data-elements-stable-field-name='cardNumber'], input"))
            )
            # Click to focus first
            card_field.click()
            time.sleep(0.2)
            card_field.clear()
            card_field.send_keys(card_number)
            driver.switch_to.default_content()
            logging.info("✅ Numéro carte saisi")
            
            # Small delay between fields
            time.sleep(0.3)
            
            # Expiry
            driver.switch_to.frame(iframes[1])
            expiry_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='exp-date'], input[placeholder*='MM'], input[data-elements-stable-field-name='cardExpiry'], input"))
            )
            expiry_field.click()
            time.sleep(0.2)
            expiry_field.clear()
            expiry_field.send_keys(card_expiry)
            driver.switch_to.default_content()
            logging.info("✅ Date expiration saisie")
            
            # Small delay
            time.sleep(0.3)
            
            # CVC
            driver.switch_to.frame(iframes[2])
            cvc_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='cvc'], input[placeholder*='CVC'], input[data-elements-stable-field-name='cardCvc'], input"))
            )
            cvc_field.click()
            time.sleep(0.2)
            cvc_field.clear()
            cvc_field.send_keys(card_cvc)
            driver.switch_to.default_content()
            logging.info("✅ CVC saisi")
            
        except Exception as e:
            driver.switch_to.default_content()  # Make sure we're out of any iframe
            logging.error(f"❌ Erreur lors du remplissage des champs: {e}")
            
            # Alternative approach - try JavaScript execution
            try:
                logging.info("🔄 Tentative avec JavaScript...")
                
                # Card number
                driver.switch_to.frame(iframes[0])
                driver.execute_script("arguments[0].focus(); arguments[0].value = arguments[1];", 
                                    driver.find_element(By.CSS_SELECTOR, "input"), card_number)
                driver.switch_to.default_content()
                
                # Expiry
                driver.switch_to.frame(iframes[1])
                driver.execute_script("arguments[0].focus(); arguments[0].value = arguments[1];", 
                                    driver.find_element(By.CSS_SELECTOR, "input"), card_expiry)
                driver.switch_to.default_content()
                
                # CVC
                driver.switch_to.frame(iframes[2])
                driver.execute_script("arguments[0].focus(); arguments[0].value = arguments[1];", 
                                    driver.find_element(By.CSS_SELECTOR, "input"), card_cvc)
                driver.switch_to.default_content()
                
                logging.info("✅ Champs remplis avec JavaScript")
            except:
                return False
        
        # Wait before submitting
        time.sleep(0.5)
        
        # Submit payment - look for the actual Pay button in the modal
        try:
            # First try the button in the modal/popup
            pay_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Pay £9.90') or contains(text(), 'Pay')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pay_button)
            time.sleep(0.3)
            pay_button.click()
            logging.info("✅ Bouton Pay cliqué")
        except:
            # Fallback to the original submit button
            try:
                submit_btn = driver.find_element(By.ID, "cs-stripe-elements-submit-button")
                driver.execute_script("arguments[0].click();", submit_btn)
                logging.info("✅ Paiement soumis (fallback)")
            except:
                logging.error("❌ Impossible de trouver le bouton de paiement")
                return False
        
        # Wait for confirmation
        try:
            WebDriverWait(driver, 30).until(
                lambda d: "confirmation" in d.current_url.lower() or "success" in d.current_url.lower()
            )
            take_screenshot("confirmation")
            logging.info("🎉 RÉSERVATION CONFIRMÉE!")
            return True
        except:
            # Check for any success indicators on page
            time.sleep(5)
            page_source = driver.page_source.lower()
            if any(word in page_source for word in ["confirmed", "success", "booked", "reserved", "confirmation"]):
                logging.info("🎉 RÉSERVATION PROBABLEMENT CONFIRMÉE!")
                take_screenshot("probable_success")
                return True
            else:
                logging.error("❌ Pas de confirmation trouvée")
                return False
        
    except Exception as e:
        logging.error(f"❌ Erreur paiement Stripe: {e}")
        take_screenshot("stripe_error")
        # Make sure we're back to default content
        try:
            driver.switch_to.default_content()
        except:
            pass
        return False

# Main execution - ULTRA FAST MODE
try:
    start_time = time.time()
    
    # Login phase
    if not login_first(username, password):
        logging.error("❌ Login impossible!")
        exit(1)
    
    # Navigate to booking page after successful login
    booking_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=member"
    logging.info(f"🌐 Navigation vers: {booking_url}")
    driver.get(booking_url)
    time.sleep(3)
    
    take_screenshot("booking_page_after_login")
    
    # Verify we're still logged in
    if not check_login_status():
        logging.error("❌ Session perdue après navigation!")
        exit(1)
    
    # Ultra-fast booking loop
    attempt = 0
    max_attempts = 500  # More attempts since they're faster
    success = False
    
    logging.info(f"🔍 Début de la recherche pour un créneau à {hour_str}")
    
    while attempt < max_attempts and (time.time() - start_time) < 300:
        attempt += 1
        elapsed = int(time.time() - start_time)
        
        # Check login status every 10 attempts
        if attempt % 10 == 0:
            if not check_login_status():
                logging.warning("⚠️ Session perdue, reconnexion...")
                if not login_first(username, password):
                    logging.error("❌ Reconnexion échouée!")
                    break
                driver.get(booking_url)
                time.sleep(2)
        
        # Log each attempt
        logging.info(f"🔄 Tentative {attempt}/{max_attempts} (temps: {elapsed}s)")
        
        # Skip the "page loaded" check - go straight to finding slots
        if ultra_fast_slot_finder():
            if complete_booking_ultra_fast():
                success = True
                logging.info("🎉 RÉSERVATION RÉUSSIE!")
                break
        
        # Ultra-fast refresh - no delay between attempts
        if attempt < max_attempts:
            driver.refresh()
            # Tiny delay only every few attempts to avoid rate limiting
            if attempt % 3 == 0:
                time.sleep(0.3)
    
    total_time = int(time.time() - start_time)
    if success:
        logging.info(f"🎉 RÉSERVATION RÉUSSIE en {total_time}s après {attempt} tentatives!")
    else:
        logging.info(f"✅ Script terminé en {total_time}s après {attempt} tentatives")

except Exception as e:
    logging.error(f"❌ Erreur critique: {e}")
    if driver:
        take_screenshot("critical_error")
finally:
    if driver:
        driver.quit()
        logging.info("🏁 Driver fermé")
