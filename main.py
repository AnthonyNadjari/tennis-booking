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

# Configuration Chrome - Added cookie persistence
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
# Keep session data
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

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

def ensure_logged_in(username, password):
    """Ensure we're logged in, login if not"""
    if check_login_status():
        logging.info("✅ Déjà connecté!")
        return True
    
    logging.info("🔐 Pas connecté, tentative de connexion...")
    return login_first(username, password)

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

def wait_for_page_load():
    """Wait for the booking page to fully load"""
    try:
        # Wait for booking links
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.book-interval"))
        )
        
        time.sleep(0.3)
        
        # Check we're not on login page
        if "login" in driver.current_url.lower():
            logging.error("❌ Redirigé vers la page de login!")
            return False
        
        logging.info("✅ Page de réservation chargée")
        return True
    except TimeoutException:
        logging.warning("⚠️ Timeout lors du chargement de la page")
        return False

def find_and_book_slot():
    try:
        # Check login status first
        if not check_login_status():
            logging.warning("⚠️ Session perdue, reconnexion nécessaire")
            return False

        # Accept cookies if needed
        try:
            cookie_btn = driver.find_element(By.CLASS_NAME, "osano-cm-accept-all")
            cookie_btn.click()
            time.sleep(0.1)
        except:
            pass

        # Wait for page to load
        if not wait_for_page_load():
            return False

        logging.info(f"🔍 Recherche créneaux à {hour_str}...")

        # Direct XPath to find slot
        target_time_minutes = hour * 60 + minutes
        xpath_query = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{target_time_minutes}')]"

        try:
            target_slot = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, xpath_query))
            )

            logging.info(f"🎯 SLOT TROUVÉ DIRECTEMENT à {hour_str}!")
            target_slot.click()
            logging.info("✅ Cliqué!")

            time.sleep(1.5)
            return complete_booking_process()

        except TimeoutException:
            logging.info("⚠️ Recherche directe échouée, méthode classique...")

            booking_links = driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked")

            for link in booking_links:
                data_test_id = link.get_attribute('data-test-id') or ""

                if '|' in data_test_id:
                    parts = data_test_id.split('|')
                    if len(parts) >= 3:
                        try:
                            if int(parts[2]) == target_time_minutes:
                                logging.info(f"🎯 SLOT TROUVÉ à {hour_str}!")
                                link.click()
                                time.sleep(1.5)
                                return complete_booking_process()
                        except:
                            continue

        logging.warning(f"⚠️ Aucun slot trouvé pour {hour_str}")
        return False

    except Exception as e:
        logging.error(f"❌ Erreur: {e}")
        return False

def complete_booking_process():
    try:
        time.sleep(1)
        
        # CRITICAL: Check we're still logged in after clicking slot
        current_url = driver.current_url
        logging.info(f"📍 URL après clic slot: {current_url}")
        
        if "login" in current_url.lower() or not check_login_status():
            logging.error("❌ Redirigé vers login après sélection du slot!")
            take_screenshot("redirected_to_login")
            return False

        # Select duration
        try:
            select2_dropdown = driver.find_element(By.CSS_SELECTOR, ".select2-selection, .select2-selection--single")
            select2_dropdown.click()
            time.sleep(0.3)

            options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
            if len(options) >= 2:
                options[1].click()
                logging.info("✅ Durée sélectionnée")
        except:
            try:
                duration_select = driver.find_element(By.ID, "booking-duration")
                Select(duration_select).select_by_index(1)
                logging.info("✅ Durée sélectionnée")
            except:
                pass

        time.sleep(0.5)

        # Click Continue
        try:
            continue_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
            continue_btn.click()
            logging.info("✅ Continue cliqué")
            time.sleep(2)  # Increased wait
        except:
            try:
                continue_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
                continue_btn.click()
                logging.info("✅ Continue cliqué (submit)")
                time.sleep(2)
            except:
                logging.error("❌ Bouton Continue non trouvé")
                return False

        # CRITICAL: Check again after Continue
        current_url = driver.current_url
        logging.info(f"📍 URL après Continue: {current_url}")
        
        if "login" in current_url.lower():
            logging.error("❌ Redirigé vers login après Continue!")
            take_screenshot("login_redirect_after_continue")
            
            # Try to re-login quickly
            if login_first(username, password):
                logging.info("✅ Re-connecté avec succès")
                # Need to restart the booking process
                return False
            else:
                logging.error("❌ Impossible de se reconnecter")
                return False
        
        # Look for payment button
        try:
            # Wait longer and check for presence first
            pay_btn = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "paynow"))
            )
            
            # Ensure it's visible and clickable
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "paynow"))
            )
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pay_btn)
            time.sleep(0.5)
            
            try:
                pay_btn.click()
            except:
                driver.execute_script("arguments[0].click();", pay_btn)
                
            logging.info("✅ Confirm and pay cliqué")
            time.sleep(2)
            
            return handle_stripe_payment()
            
        except TimeoutException:
            logging.error("❌ Bouton payment non trouvé")
            take_screenshot("payment_button_not_found")
            
            # Log current page info
            logging.info(f"🔍 Titre page: {driver.title}")
            buttons = driver.find_elements(By.TAG_NAME, "button")
            logging.info(f"🔘 {len(buttons)} boutons sur la page")
            
            return False

    except Exception as e:
        logging.error(f"❌ Erreur booking: {e}")
        take_screenshot("booking_error")
        return False

def handle_stripe_payment():
    try:
        logging.info("💳 Traitement paiement Stripe...")
        
        # Check one more time we're not on login page
        if "login" in driver.current_url.lower():
            logging.error("❌ Sur la page de login au lieu de Stripe!")
            return False
        
        take_screenshot("stripe_form")

        # Wait for Stripe iframes
        iframes = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
        )
        logging.info(f"✅ {len(iframes)} iframes Stripe trouvées")

        if len(iframes) < 3:
            logging.error("❌ Pas assez d'iframes Stripe")
            return False

        # Fill payment details
        # Card number
        driver.switch_to.frame(iframes[0])
        card_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cardnumber'], input[placeholder*='card'], input[data-elements-stable-field-name='cardNumber']"))
        )
        card_field.clear()
        card_field.send_keys(card_number)
        driver.switch_to.default_content()
        logging.info("✅ Numéro carte saisi")

        # Expiry date
        driver.switch_to.frame(iframes[1])
        expiry_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='exp-date'], input[placeholder*='MM'], input[data-elements-stable-field-name='cardExpiry']"))
        )
        expiry_field.clear()
        expiry_field.send_keys(card_expiry)
        driver.switch_to.default_content()
        logging.info("✅ Date expiration saisie")

        # CVC
        driver.switch_to.frame(iframes[2])
        cvc_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cvc'], input[placeholder*='CVC'], input[data-elements-stable-field-name='cardCvc']"))
        )
        cvc_field.clear()
        cvc_field.send_keys(card_cvc)
        driver.switch_to.default_content()
        logging.info("✅ CVC saisi")

        # Submit payment
        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(0.5)
        submit_btn.click()
        logging.info("✅ Paiement soumis")

        # Wait for confirmation
        try:
            WebDriverWait(driver, 30).until(
                lambda d: "confirmation" in d.current_url.lower() or "success" in d.current_url.lower()
            )
            take_screenshot("confirmation")
            logging.info("🎉 RÉSERVATION CONFIRMÉE!")
            return True
        except:
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
        return False

# Main execution
try:
    start_time = time.time()
    max_duration = 300

    # Initial login
    logging.info("🔐 Connexion initiale...")
    login_success = login_first(username, password)
    
    if not login_success:
        logging.error("❌ Impossible de se connecter!")
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

    # Booking loop
    attempt = 0
    max_attempts = 300

    while attempt < max_attempts and (time.time() - start_time) < max_duration:
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
        
        logging.info(f"🔄 Tentative {attempt}/{max_attempts} (temps: {elapsed}s)")

        if find_and_book_slot():
            logging.info("🎉 RÉSERVATION RÉUSSIE!")
            break
        else:
            if attempt < max_attempts and (time.time() - start_time) < max_duration - 10:
                # Fast refresh
                driver.refresh()
                # Small wait to avoid rate limiting
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
