from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
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
username = os.environ.get('TENNIS_USERNAME')
password = os.environ.get('TENNIS_PASSWORD')
card_number = os.environ.get('CARD_NUMBER', '5354562794845156')
card_expiry = os.environ.get('CARD_EXPIRY', '04/30')
card_cvc = os.environ.get('CARD_CVC', '666')
date = os.environ.get('BOOKING_DATE', '2025-06-16')
hour = int(os.environ.get('BOOKING_HOUR', '7'))

if not username or not password:
    logging.error("❌ TENNIS_USERNAME ou TENNIS_PASSWORD non définis!")
    exit(1)

hour_str = f"{hour:02d}:00"
hour_system_minutes = hour * 60
next_hour = f"{hour + 1:02d}:00"

logging.info(f"🎾 Réservation pour le {date} à {hour_str}")
logging.info(f"⏰ Minutes système: {hour_system_minutes}")

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
            time.sleep(2)
        except Exception as e:
            logging.warning(f"Sign in non trouvé: {e}")

        # Step 2: Click Login button
        try:
            login_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Log in')]"))
            )
            login_btn.click()
            logging.info("✅ Cliqué sur Login")
            time.sleep(2)
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
            
            time.sleep(3)
            return True

        except Exception as e:
            logging.error(f"Erreur saisie credentials: {e}")
            return False

    except Exception as e:
        logging.error(f"❌ Erreur login: {e}")
        take_screenshot("login_error")
        return False

def find_and_book_slot():
    try:
        # Accept cookies
        try:
            cookie_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "osano-cm-accept-all"))
            )
            cookie_btn.click()
            logging.info("✅ Cookies acceptés")
            time.sleep(1)
        except:
            pass

        # Wait for page to load completely
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.resource"))
        )
        time.sleep(3)  # Additional wait for dynamic content

        logging.info(f"🔍 Recherche créneaux disponibles à {hour_str}...")
        
        # Method 1: Look for available slots using the highlighted class structure
        # Based on your screenshot, look for elements with class "not-booked"
        available_slots = driver.find_elements(By.CSS_SELECTOR, 'a.not-booked')
        logging.info(f"📊 {len(available_slots)} créneaux 'not-booked' trouvés")
        
        # Also try the original selector as backup
        if not available_slots:
            available_slots = driver.find_elements(By.CSS_SELECTOR, 'a.book-interval.not-booked')
            logging.info(f"📊 {len(available_slots)} créneaux 'book-interval not-booked' trouvés")
        
        # Also try just looking for book-interval elements and check if they're available
        if not available_slots:
            all_intervals = driver.find_elements(By.CSS_SELECTOR, 'a.book-interval')
            available_slots = [slot for slot in all_intervals if 'not-booked' in slot.get_attribute('class')]
            logging.info(f"📊 {len(available_slots)} créneaux via filtrage manuel trouvés")

        # Check each slot
        for i, slot in enumerate(available_slots):
            try:
                slot_text = slot.text.strip()
                data_test_id = slot.get_attribute('data-test-id') or ""
                class_attr = slot.get_attribute('class') or ""
                href_attr = slot.get_attribute('href') or ""
                
                logging.info(f"🔍 Slot {i+1}: '{slot_text}' | class: '{class_attr}' | data-test-id: '{data_test_id}'")
                
                # Check if this slot matches our desired time
                time_match = (
                    hour_str in slot_text or
                    f"|{hour_system_minutes}|" in data_test_id or
                    f"|{hour_system_minutes}" in data_test_id or
                    f"={hour_system_minutes}" in href_attr
                )
                
                # Check for price to confirm it's bookable
                has_price = any(price in slot_text for price in ["£3.60", "£4.95", "£3.50", "£5.00", "£6.00", "£"])
                
                # Check if it's truly available (not booked)
                is_available = (
                    'not-booked' in class_attr and 
                    'booked' not in class_attr.replace('not-booked', '')
                )
                
                logging.info(f"   Time match: {time_match}, Has price: {has_price}, Available: {is_available}")
                
                if time_match and has_price and is_available:
                    logging.info(f"✅ CRÉNEAU TROUVÉ: {slot_text}")
                    
                    # Scroll to element
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", slot)
                    time.sleep(1)
                    
                    # Click the slot
                    try:
                        slot.click()
                    except:
                        driver.execute_script("arguments[0].click();", slot)
                    
                    logging.info("✅ Créneau cliqué")
                    time.sleep(2)
                    
                    return complete_booking_process()
                    
            except Exception as e:
                logging.warning(f"Erreur vérification slot {i+1}: {e}")
                continue

        # Method 2: Look for specific time intervals using data attributes
        logging.info("🔍 Méthode alternative: recherche par intervalle de temps...")
        
        # Try different selectors for time intervals
        time_selectors = [
            f'div[data-system-start-time="{hour_system_minutes}"]',
            f'*[data-start-time="{hour_system_minutes}"]',
            f'*[data-system-start-time="{hour_system_minutes}"]'
        ]
        
        for selector in time_selectors:
            time_intervals = driver.find_elements(By.CSS_SELECTOR, selector)
            logging.info(f"Found {len(time_intervals)} intervals with selector: {selector}")
            
            for interval in time_intervals:
                try:
                    # Look for booking link within this time interval
                    parent = interval.find_element(By.XPATH, "./..")
                    
                    # Try different ways to find the booking link
                    booking_selectors = [
                        'a.not-booked',
                        'a.book-interval.not-booked',
                        'a.book-interval'
                    ]
                    
                    booking_link = None
                    for book_selector in booking_selectors:
                        try:
                            booking_link = parent.find_element(By.CSS_SELECTOR, book_selector)
                            if 'not-booked' in booking_link.get_attribute('class'):
                                break
                        except:
                            continue
                    
                    if booking_link and "£" in booking_link.text:
                        logging.info(f"✅ Créneau trouvé via intervalle: {booking_link.text}")
                        driver.execute_script("arguments[0].click();", booking_link)
                        time.sleep(2)
                        return complete_booking_process()
                        
                except Exception as e:
                    logging.debug(f"Erreur interval check: {e}")
                    continue

        # Method 3: Advanced search using XPath
        logging.info("🔍 Méthode XPath avancée...")
        xpath_queries = [
            f"//a[contains(@class, 'not-booked') and contains(text(), '{hour_str}')]",
            f"//a[contains(@class, 'not-booked') and contains(@data-test-id, '|{hour_system_minutes}|')]",
            f"//a[contains(@class, 'not-booked') and contains(., '£')]//ancestor-or-self::*[contains(text(), '{hour_str}')]"
        ]
        
        for xpath in xpath_queries:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                logging.info(f"XPath '{xpath}' found {len(elements)} elements")
                
                for element in elements:
                    if "£" in element.text:
                        logging.info(f"✅ Créneau trouvé via XPath: {element.text}")
                        driver.execute_script("arguments[0].click();", element)
                        time.sleep(2)
                        return complete_booking_process()
            except Exception as e:
                logging.debug(f"XPath error: {e}")

        # Debug: Print all available slots for analysis
        logging.info("🔍 Debug: Analyse de tous les créneaux...")
        all_links = driver.find_elements(By.CSS_SELECTOR, 'a')
        available_count = 0
        
        for link in all_links:
            class_attr = link.get_attribute('class') or ""
            if 'book' in class_attr.lower() or 'not-booked' in class_attr:
                text = link.text.strip()
                if text and len(text) < 100:  # Avoid very long texts
                    logging.info(f"   Link: '{text}' | class: '{class_attr}'")
                    available_count += 1
                    
                    if available_count > 20:  # Limit debug output
                        break

        logging.warning("❌ Aucun créneau disponible trouvé")
        take_screenshot("no_slots_found")
        return False

    except Exception as e:
        logging.error(f"❌ Erreur find_and_book_slot: {e}")
        take_screenshot("find_slot_error")
        return False
    except Exception as e:
        logging.error(f"❌ Erreur find_and_book_slot: {e}")
        take_screenshot("find_slot_error")
        return False

def complete_booking_process():
    try:
        take_screenshot("booking_form")
        
        # Handle duration selection using the proven method
        try:
            # Try Select2 dropdown first (modern approach)
            select2_selection = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".select2-selection"))
            )
            select2_selection.click()
            time.sleep(0.5)
            
            # Select the second option (1 hour duration)
            options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
            if len(options) >= 2:
                options[1].click()
                logging.info("✅ Durée sélectionnée (Select2)")
            else:
                # Fallback: look for specific next hour option
                next_hour_option = driver.find_element(By.XPATH, f"//li[contains(text(), '{next_hour}')]")
                next_hour_option.click()
                logging.info("✅ Durée sélectionnée (texte spécifique)")
                
        except Exception as e:
            logging.warning(f"Select2 échoué, fallback vers select standard: {e}")
            # Fallback to hidden select element
            try:
                hidden_select = driver.find_element(By.ID, "booking-duration")
                Select(hidden_select).select_by_index(1)
                logging.info("✅ Durée sélectionnée (select caché)")
            except Exception as e2:
                logging.warning(f"Select caché échoué: {e2}")

        time.sleep(0.5)

        # Click Continue button
        try:
            continue_btn = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]"))
            )
            continue_btn.click()
            logging.info("✅ Continue cliqué")
        except:
            # Alternative: try submit button
            try:
                submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                submit_btn.click()
                logging.info("✅ Continue cliqué (submit)")
            except Exception as e:
                logging.error(f"Erreur Continue: {e}")
                return False

        time.sleep(3)

        # Click Pay Now / Confirm and pay
        try:
            paynow_btn = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.ID, "paynow"))
            )
            paynow_btn.click()
            logging.info("✅ Pay Now cliqué")
        except:
            # JavaScript fallback
            try:
                driver.execute_script("document.getElementById('paynow').click();")
                logging.info("✅ Pay Now cliqué (JavaScript)")
            except:
                # Text-based fallback
                try:
                    confirm_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm')]")
                    confirm_btn.click()
                    logging.info("✅ Confirm cliqué (texte)")
                except Exception as e:
                    logging.error(f"Erreur Pay Now: {e}")
                    return False

        time.sleep(3)

        # Handle Stripe payment
        return handle_stripe_payment()

    except Exception as e:
        logging.error(f"❌ Erreur complete_booking_process: {e}")
        take_screenshot("booking_process_error")
        return False

def handle_stripe_payment():
    try:
        logging.info("💳 Traitement paiement Stripe (méthode améliorée)...")
        take_screenshot("stripe_form")
        
        # Wait for Stripe iframes to load
        time.sleep(2)
        
        # Get all Stripe iframes
        stripe_iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[name*='privateStripeFrame']")
        logging.info(f"✅ {len(stripe_iframes)} iframes Stripe trouvées")

        if len(stripe_iframes) < 3:
            logging.error("❌ Pas assez d'iframes Stripe")
            return False

        # Card number (first iframe)
        try:
            driver.switch_to.frame(stripe_iframes[0])
            card_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cardnumber']"))
            )
            card_field.send_keys(card_number)
            driver.switch_to.default_content()
            logging.info("✅ Numéro carte saisi")
        except Exception as e:
            logging.error(f"Erreur carte: {e}")
            driver.switch_to.default_content()

        # Expiry date (try all iframes until we find the right one)
        expiry_success = False
        for iframe in stripe_iframes:
            try:
                driver.switch_to.frame(iframe)
                expiry_field = driver.find_element(By.CSS_SELECTOR, "input[name='exp-date']")
                expiry_field.send_keys(card_expiry)
                driver.switch_to.default_content()
                logging.info("✅ Date expiration saisie")
                expiry_success = True
                break
            except:
                driver.switch_to.default_content()
                continue

        # CVC (look for iframe with CVC in title or try remaining iframes)
        cvc_success = False
        try:
            cvc_iframe = driver.find_element(By.CSS_SELECTOR, "iframe[title*='CVC']")
            driver.switch_to.frame(cvc_iframe)
            cvc_field = driver.find_element(By.CSS_SELECTOR, "input[name='cvc']")
            cvc_field.send_keys(card_cvc)
            driver.switch_to.default_content()
            logging.info("✅ CVC saisi")
            cvc_success = True
        except:
            driver.switch_to.default_content()
            # Try remaining iframes
            for iframe in stripe_iframes:
                try:
                    driver.switch_to.frame(iframe)
                    cvc_field = driver.find_element(By.CSS_SELECTOR, "input[name='cvc']")
                    cvc_field.send_keys(card_cvc)
                    driver.switch_to.default_content()
                    logging.info("✅ CVC saisi (fallback)")
                    cvc_success = True
                    break
                except:
                    driver.switch_to.default_content()
                    continue

        # Submit payment
        try:
            pay_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
            )
            pay_button.click()
            logging.info("✅ Paiement soumis")
        except Exception as e:
            logging.error(f"Erreur soumission paiement: {e}")
            return False

        # Wait for confirmation
        time.sleep(5)
        
        # Check for success indicators
        page_source = driver.page_source.lower()
        current_url = driver.current_url.lower()
        
        if any(indicator in page_source for indicator in ["confirmed", "success", "booked", "reserved"]) or \
           any(indicator in current_url for indicator in ["confirmation", "success"]):
            logging.info("🎉 RÉSERVATION CONFIRMÉE!")
            take_screenshot("confirmation")
            return True
        else:
            logging.error("❌ Pas de confirmation trouvée")
            take_screenshot("payment_result")
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
    time.sleep(3)
    take_screenshot("initial_page")

    # Login
    login_success = login_first(username, password)
    if login_success:
        logging.info("✅ Login réussi")
    else:
        logging.warning("⚠️ Login échoué, on continue...")
    
    # Navigate to booking page again if needed
    if "BookByDate" not in driver.current_url:
        driver.get(url)
        time.sleep(3)

    # Try booking with retry loop
    attempt = 0
    max_attempts = 10
    
    while attempt < max_attempts and (time.time() - start_time) < max_duration:
        attempt += 1
        elapsed = int(time.time() - start_time)
        logging.info(f"🔄 Tentative {attempt}/{max_attempts} (temps: {elapsed}s)")
        
        if find_and_book_slot():
            logging.info("🎉 RÉSERVATION RÉUSSIE!")
            break
        else:
            if attempt < max_attempts and (time.time() - start_time) < max_duration - 10:
                logging.info("⏳ Actualisation dans 2 secondes...")
                time.sleep(2)
                driver.refresh()
                time.sleep(2)
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
