from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import logging
from datetime import datetime

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

# Initialize driver
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
        logging.info(f"📸 Screenshot: {filename}")
    except Exception as e:
        logging.error(f"Erreur screenshot: {e}")

def login_first(username, password):
    try:
        # Check if already logged in
        current_page = driver.page_source
        if "My bookings" in current_page or "Log out" in current_page:
            logging.info("✅ Déjà connecté!")
            return True

        logging.info("🔐 Processus de connexion...")
        
        # Step 1: Click Sign in
        try:
            sign_in_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in') or contains(@href, 'login')]"))
            )
            sign_in_link.click()
            logging.info("✅ Cliqué sur Sign in")
            time.sleep(1)
        except Exception as e:
            logging.warning(f"Sign in non trouvé: {e}")

        # Step 2: Click Login button
        try:
            login_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Log in')]"))
            )
            login_btn.click()
            logging.info("✅ Cliqué sur Login")
            time.sleep(1)
        except Exception as e:
            logging.warning(f"Login button non trouvé: {e}")

        # Step 3: Fill credentials
        try:
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Username' or @name='username' or @id='username']"))
            )
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
            
            time.sleep(2)
            return True

        except Exception as e:
            logging.error(f"Erreur saisie credentials: {e}")
            return False

    except Exception as e:
        logging.error(f"❌ Erreur login: {e}")
        take_screenshot("login_error")
        return False

def wait_for_page_load():
    """Wait for the booking page to fully load"""
    try:
        # Wait for the main booking grid to be present
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.resource, .booking-grid, .session-container"))
        )
        
        # Wait a bit more for dynamic content to load
        time.sleep(2)
        
        # Wait for at least some booking slots to be present
        WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[class*='book'], .book-interval, a.not-booked"))
        )
        
        logging.info("✅ Page de réservation chargée")
        return True
    except TimeoutException:
        logging.warning("⚠️ Timeout lors du chargement de la page")
        return False

def find_and_book_slot():
    try:
        # Accept cookies first
        try:
            cookie_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "osano-cm-accept-all"))
            )
            cookie_btn.click()
            logging.info("✅ Cookies acceptés")
            time.sleep(0.5)
        except:
            pass

        # Wait for page to load completely
        if not wait_for_page_load():
            logging.error("❌ Page non chargée correctement")
            return False

        logging.info(f"🔍 Recherche créneaux disponibles à {hour_str}...")
        
        # Debug: Log all available booking links
        try:
            all_links = driver.find_elements(By.CSS_SELECTOR, "a[class*='book'], a.not-booked")
            logging.info(f"📊 Total liens de réservation trouvés: {len(all_links)}")
            
            for i, link in enumerate(all_links[:10]):  # Log first 10 for debugging
                try:
                    link_class = link.get_attribute('class') or ""
                    link_text = link.text.strip()
                    link_href = link.get_attribute('href') or ""
                    logging.info(f"   Link {i+1}: class='{link_class}' text='{link_text}' href='{link_href[:100]}...'")
                except:
                    continue
        except Exception as e:
            logging.warning(f"Debug logging failed: {e}")

        # Method 1: Look for available slots using multiple selectors
        selectors_to_try = [
            'a.not-booked',  # Primary selector from screenshot
            'a.book-interval.not-booked',  # Original selector
            'a[class*="not-booked"]',  # Any element with not-booked in class
            'a[href*="booking"]',  # Any booking link
        ]
        
        available_slots = []
        for selector in selectors_to_try:
            try:
                slots = driver.find_elements(By.CSS_SELECTOR, selector)
                # Filter out booked slots
                filtered_slots = []
                for slot in slots:
                    class_attr = slot.get_attribute('class') or ""
                    # Make sure it's not booked (avoid "not-booked" being part of a larger class like "booked-not-booked")
                    if 'not-booked' in class_attr and not ('booked' in class_attr.replace('not-booked', '')):
                        filtered_slots.append(slot)
                
                if filtered_slots:
                    available_slots = filtered_slots
                    logging.info(f"📊 {len(available_slots)} créneaux trouvés avec selector: {selector}")
                    break
            except Exception as e:
                logging.warning(f"Selector {selector} failed: {e}")
                continue

        if not available_slots:
            logging.warning("⚠️ Aucun créneau disponible trouvé")
            return False

        # Check each slot for our desired time
        for i, slot in enumerate(available_slots):
            try:
                slot_text = slot.text.strip()
                data_test_id = slot.get_attribute('data-test-id') or ""
                class_attr = slot.get_attribute('class') or ""
                href_attr = slot.get_attribute('href') or ""
                
                logging.info(f"🔍 Analyzing slot {i+1}: '{slot_text}'")
                logging.info(f"   Class: '{class_attr}'")
                logging.info(f"   Data-test-id: '{data_test_id}'")
                
                # Enhanced time matching logic
                time_matches = [
                    hour_str in slot_text,  # Direct time match (e.g., "07:00")
                    f"{hour:02d}:{minutes:02d}" in slot_text,  # Exact time format
                    str(hour_system_minutes) in data_test_id,  # Minutes in data attribute
                    str(hour_system_minutes) in href_attr,  # Minutes in href
                ]
                
                # Also check for common time formats
                time_variants = [
                    f"{hour}:{minutes:02d}",  # 7:00
                    f"{hour:02d}.{minutes:02d}",  # 07.00
                    f"{hour:02d}{minutes:02d}",  # 0700
                ]
                
                for variant in time_variants:
                    time_matches.append(variant in slot_text)
                
                time_match = any(time_matches)
                
                # Check for price indicators (available slots usually show prices)
                price_indicators = ["£", "€", "$", "GBP", "price"]
                has_price = any(indicator in slot_text.lower() for indicator in price_indicators)
                
                # Verify it's truly available
                is_available = (
                    'not-booked' in class_attr and 
                    'booked' not in class_attr.replace('not-booked', '') and
                    not any(unavailable in class_attr.lower() for unavailable in ['disabled', 'unavailable', 'closed'])
                )
                
                logging.info(f"   Time match: {time_match}")
                logging.info(f"   Has price: {has_price}")
                logging.info(f"   Is available: {is_available}")
                
                if time_match and is_available:
                    logging.info(f"✅ CRÉNEAU TROUVÉ: {slot_text}")
                    
                    # Scroll to element and click
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", slot)
                        time.sleep(0.5)
                        
                        # Try clicking with multiple methods
                        try:
                            slot.click()
                        except ElementClickInterceptedException:
                            # Try JavaScript click if regular click is intercepted
                            driver.execute_script("arguments[0].click();", slot)
                        
                        logging.info("✅ Créneau cliqué")
                        time.sleep(1)
                        
                        return complete_booking_process()
                        
                    except Exception as click_error:
                        logging.error(f"Erreur lors du clic: {click_error}")
                        continue
                    
            except Exception as e:
                logging.warning(f"Erreur vérification slot {i+1}: {e}")
                continue

        # Method 2: Time-based search using parent containers
        logging.info("🔍 Méthode alternative: recherche par containers de temps...")
        
        try:
            # Look for time containers that match our hour
            time_containers = driver.find_elements(By.XPATH, f"//div[contains(text(), '{hour_str}') or contains(text(), '{hour}:')]")
            
            for container in time_containers:
                try:
                    # Look for booking links in the same row/section
                    parent = container.find_element(By.XPATH, "./ancestor::div[contains(@class, 'resource') or contains(@class, 'session')]")
                    booking_links = parent.find_elements(By.CSS_SELECTOR, "a.not-booked, a[class*='not-booked']")
                    
                    for link in booking_links:
                        if 'not-booked' in link.get_attribute('class'):
                            logging.info(f"✅ Créneau trouvé via container: {link.text}")
                            driver.execute_script("arguments[0].click();", link)
                            time.sleep(1)
                            return complete_booking_process()
                            
                except Exception as e:
                    continue
        except Exception as e:
            logging.warning(f"Méthode alternative échouée: {e}")

        return False

    except Exception as e:
        logging.error(f"❌ Erreur find_and_book_slot: {e}")
        take_screenshot("find_slot_error")
        return False

def complete_booking_process():
    try:
        take_screenshot("booking_form")
        
        # Wait for booking form to load
        time.sleep(2)
        
        # Select duration if needed
        try:
            # Try Select2 dropdown first
            select2_dropdown = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".select2-selection, .select2-selection--single"))
            )
            select2_dropdown.click()
            time.sleep(0.5)
            
            # Select 1 hour option (usually second option)
            options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
            if len(options) >= 2:
                options[1].click()
                logging.info("✅ Durée sélectionnée (Select2)")
            
        except:
            # Fallback to regular select
            try:
                duration_select = driver.find_element(By.ID, "booking-duration")
                Select(duration_select).select_by_index(1)
                logging.info("✅ Durée sélectionnée (select)")
            except:
                logging.info("⚠️ Pas de sélection durée nécessaire")

        time.sleep(1)

        # Click Continue
        try:
            continue_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue') or contains(text(), 'Next')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_btn)
            time.sleep(0.5)
            continue_btn.click()
            logging.info("✅ Continue cliqué")
            time.sleep(2)
        except Exception as e:
            logging.error(f"Erreur Continue: {e}")
            return False

        # Click Pay Now
        try:
            pay_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "paynow"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pay_btn)
            time.sleep(0.5)
            pay_btn.click()
            logging.info("✅ Pay Now cliqué")
            time.sleep(2)
        except Exception as e:
            logging.error(f"Erreur Pay Now: {e}")
            return False

        # Handle Stripe payment
        return handle_stripe_payment()

    except Exception as e:
        logging.error(f"❌ Erreur complete_booking_process: {e}")
        take_screenshot("booking_process_error")
        return False

def handle_stripe_payment():
    try:
        logging.info("💳 Traitement paiement Stripe...")
        take_screenshot("stripe_form")
        
        # Wait for Stripe iframes to load
        iframes = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
        )
        logging.info(f"✅ {len(iframes)} iframes Stripe trouvées")

        if len(iframes) < 3:
            logging.error("❌ Pas assez d'iframes Stripe")
            return False

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
            # Check for any success indicators on page
            time.sleep(5)
            page_source = driver.page_source.lower()
            if any(word in page_source for word in ["confirmed", "success", "booked", "reserved"]):
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
    max_duration = 300  # 5 minutes max
    
    # Navigate to booking page
    url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=guest"
    logging.info(f"🌐 Navigation: {url}")
    driver.get(url)
    time.sleep(3)  # Give more time for initial page load
    take_screenshot("initial_page")

    # Login
    login_success = login_first(username, password)
    is_logged_in = login_success
    
    if login_success:
        logging.info("✅ Login réussi - Mode optimisé activé")
    else:
        logging.warning("⚠️ Login échoué, on continue...")
    
    # Navigate to booking page again if needed
    if "BookByDate" not in driver.current_url:
        driver.get(url)
        time.sleep(3)

    # Try booking with optimized retry loop
    attempt = 0
    max_attempts = 300 if is_logged_in else 10
    
    while attempt < max_attempts and (time.time() - start_time) < max_duration:
        attempt += 1
        elapsed = int(time.time() - start_time)
        logging.info(f"🔄 Tentative {attempt}/{max_attempts} (temps: {elapsed}s)")
        
        if find_and_book_slot():
            logging.info("🎉 RÉSERVATION RÉUSSIE!")
            break
        else:
            if attempt < max_attempts and (time.time() - start_time) < max_duration - 10:
                refresh_delay = 1.5 if is_logged_in else 3.0
                logging.info(f"⏳ Actualisation dans {refresh_delay}s...")
                time.sleep(refresh_delay)
                driver.refresh()
                time.sleep(2)  # Give time for page to reload
            else:
                break

    total_time = int(time.time() - start_time)
    logging.info(f"✅ Script terminé en {total_time}s après {attempt} tentatives")

except Exception as e:
    logging.error(f"❌ Erreur critique: {e}")
    take_screenshot("critical_error")
finally:
    driver.quit()
    logging.info("🏁 Driver fermé")
