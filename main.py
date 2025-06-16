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
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.resource, .booking-grid, .session-container"))
        )
        
        # Wait a bit more for dynamic content to load
        time.sleep(3)
        
        # Wait for at least some booking slots to be present
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.book-interval"))
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
        
        # FIXED: Use the correct selector for available slots
        # Based on your HTML, available slots have class "book-interval not-booked"
        available_slots = driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked")
        
        logging.info(f"📊 Total créneaux disponibles trouvés: {len(available_slots)}")
        
        if not available_slots:
            logging.warning("⚠️ Aucun créneau disponible trouvé")
            return False

        # Debug: Log details of available slots
        for i, slot in enumerate(available_slots[:5]):  # Log first 5 for debugging
            try:
                data_test_id = slot.get_attribute('data-test-id') or ""
                href = slot.get_attribute('href') or ""
                inner_html = slot.get_attribute('innerHTML') or ""
                logging.info(f"   Slot {i+1}: data-test-id='{data_test_id}'")
                logging.info(f"   Slot {i+1}: href='{href}'")
                logging.info(f"   Slot {i+1}: innerHTML='{inner_html[:100]}...'")
            except:
                continue

        # FIXED: Better time matching logic
        # From your HTML, the time info is in the data-test-id attribute
        # Format: "booking-xxxxx|2025-06-23|600" where 600 = 10:00 (600 minutes from midnight)
        target_minutes = hour * 60 + minutes
        logging.info(f"🎯 Recherche créneaux pour {target_minutes} minutes ({hour_str})")
        
        for i, slot in enumerate(available_slots):
            try:
                data_test_id = slot.get_attribute('data-test-id') or ""
                
                # Extract time from data-test-id
                # Format: booking-xxxxx|date|minutes
                if '|' in data_test_id:
                    parts = data_test_id.split('|')
                    if len(parts) >= 3:
                        slot_minutes = parts[-1]  # Last part should be minutes
                        
                        # Convert to integer and compare
                        try:
                            slot_minutes_int = int(slot_minutes)
                            slot_hour = slot_minutes_int // 60
                            slot_min = slot_minutes_int % 60
                            slot_time_str = f"{slot_hour:02d}:{slot_min:02d}"
                            
                            logging.info(f"🕐 Slot {i+1}: {slot_time_str} ({slot_minutes_int} minutes)")
                            
                            # Check if this matches our target time
                            if slot_minutes_int == target_minutes:
                                logging.info(f"✅ CRÉNEAU TROUVÉ: {slot_time_str}")
                                
                                # Scroll to element and click
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", slot)
                                    time.sleep(1)
                                    
                                    # Try clicking with multiple methods
                                    try:
                                        slot.click()
                                        logging.info("✅ Créneau cliqué (direct)")
                                    except ElementClickInterceptedException:
                                        # Try JavaScript click if regular click is intercepted
                                        driver.execute_script("arguments[0].click();", slot)
                                        logging.info("✅ Créneau cliqué (JavaScript)")
                                    
                                    time.sleep(2)
                                    return complete_booking_process()
                                    
                                except Exception as click_error:
                                    logging.error(f"Erreur lors du clic: {click_error}")
                                    continue
                        except ValueError:
                            logging.warning(f"Impossible de convertir '{slot_minutes}' en minutes")
                            continue
                    
            except Exception as e:
                logging.warning(f"Erreur vérification slot {i+1}: {e}")
                continue

        # FALLBACK: If exact time match fails, try text-based matching
        logging.info("🔍 Fallback: recherche par texte...")
        
        for i, slot in enumerate(available_slots):
            try:
                # Get all text content from the slot
                slot_text = slot.text.strip()
                inner_html = slot.get_attribute('innerHTML') or ""
                
                # Check for time patterns in text and HTML
                time_patterns = [
                    hour_str,  # 07:00
                    f"{hour}:{minutes:02d}",  # 7:00
                    f"{hour:02d}.{minutes:02d}",  # 07.00
                    f"{hour:02d}{minutes:02d}",  # 0700
                ]
                
                time_found = False
                for pattern in time_patterns:
                    if pattern in slot_text or pattern in inner_html:
                        time_found = True
                        break
                
                if time_found:
                    logging.info(f"✅ CRÉNEAU TROUVÉ (fallback): {slot_text}")
                    
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", slot)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", slot)
                        logging.info("✅ Créneau cliqué (fallback)")
                        time.sleep(2)
                        return complete_booking_process()
                    except Exception as click_error:
                        logging.error(f"Erreur clic fallback: {click_error}")
                        continue
                    
            except Exception as e:
                logging.warning(f"Erreur fallback slot {i+1}: {e}")
                continue

        logging.warning(f"⚠️ Aucun créneau trouvé pour {hour_str}")
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
                time.sleep(3)  # Give more time for page to reload
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
