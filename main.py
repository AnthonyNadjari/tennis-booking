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
        current_page = driver.page_source
        if "My bookings" in current_page or "Log out" in current_page:
            logging.info("✅ Déjà connecté!")
            return True

        logging.info("🔐 Processus de connexion...")

        try:
            sign_in_link = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in') or contains(@href, 'login')]"))
            )
            sign_in_link.click()
            logging.info("✅ Cliqué sur Sign in")
            time.sleep(2)
        except Exception as e:
            logging.warning(f"Sign in non trouvé: {e}")

        try:
            username_field = WebDriverWait(driver, 15).until(
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
            take_screenshot("login_error")
            return False

    except Exception as e:
        logging.error(f"❌ Erreur login: {e}")
        take_screenshot("login_error")
        return False

def wait_for_page_load():
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.book-interval"))
        )
        time.sleep(0.3)
        return True
    except TimeoutException:
        logging.warning("⚠️ Timeout lors du chargement de la page")
        return False

def find_and_book_slot():
    try:
        # Accept cookies if present
        try:
            cookie_btn = driver.find_element(By.CLASS_NAME, "osano-cm-accept-all")
            cookie_btn.click()
            time.sleep(0.1)
        except:
            pass

        if not wait_for_page_load():
            return False

        logging.info(f"🔍 Recherche créneaux à {hour_str}...")

        # Find ALL available slots at target time
        xpath_query = f"//a[contains(@class, 'book-interval') and contains(@class, 'not-booked') and contains(@data-test-id, '|{total_minutes}') and not(contains(@class, 'disabled'))]"
        
        try:
            slots = driver.find_elements(By.XPATH, xpath_query)
            
            if slots:
                for slot in slots:
                    try:
                        # Get court info for logging
                        data_test_id = slot.get_attribute('data-test-id')
                        court_info = data_test_id.split('|')[0] if data_test_id else "Court inconnu"
                        logging.info(f"🎯 SLOT TROUVÉ sur {court_info} à {hour_str}!")
                        
                        # Scroll and click
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", slot)
                        slot.click()
                        logging.info("✅ Cliqué!")
                        
                        if complete_booking_process():
                            return True
                    except ElementClickInterceptedException:
                        continue
                    except Exception as e:
                        logging.warning(f"Erreur click sur {court_info}: {e}")
                        continue

            logging.debug(f"⚠️ Aucun slot trouvé pour {hour_str}")
            return False

        except Exception as e:
            logging.warning(f"Recherche slots échouée: {e}")
            return False

    except Exception as e:
        logging.error(f"❌ Erreur: {e}")
        return False

def complete_booking_process():
    try:
        time.sleep(0.3)
        
        # Select duration
        try:
            select2_dropdown = driver.find_element(By.CSS_SELECTOR, ".select2-selection, .select2-selection--single")
            select2_dropdown.click()
            time.sleep(0.2)
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

        # Click Continue
        try:
            continue_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
            continue_btn.click()
            logging.info("✅ Continue cliqué")
        except:
            try:
                continue_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
                continue_btn.click()
                logging.info("✅ Continue cliqué (submit)")
            except:
                logging.error("❌ Bouton Continue non trouvé")
                return False

        # Click Pay Now
        try:
            pay_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, "paynow"))
            )
            pay_btn.click()
            logging.info("✅ Pay Now cliqué")
        except:
            logging.error("❌ Bouton Pay Now non trouvé")
            return False

        return handle_stripe_payment()

    except Exception as e:
        logging.error(f"❌ Erreur booking: {e}")
        return False

def handle_stripe_payment():
    try:
        logging.info("💳 Traitement paiement Stripe...")
        take_screenshot("stripe_form")

        iframes = WebDriverWait(driver, 12).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
        )
        logging.info(f"✅ {len(iframes)} iframes Stripe trouvées")

        if len(iframes) < 3:
            logging.error("❌ Pas assez d'iframes Stripe")
            return False

        # Card number
        driver.switch_to.frame(iframes[0])
        card_field = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cardnumber'], input[placeholder*='card'], input[data-elements-stable-field-name='cardNumber']"))
        )
        card_field.clear()
        card_field.send_keys(card_number)
        driver.switch_to.default_content()
        logging.info("✅ Numéro carte saisi")

        # Expiry date
        driver.switch_to.frame(iframes[1])
        expiry_field = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='exp-date'], input[placeholder*='MM'], input[data-elements-stable-field-name='cardExpiry']"))
        )
        expiry_field.clear()
        expiry_field.send_keys(card_expiry)
        driver.switch_to.default_content()
        logging.info("✅ Date expiration saisie")

        # CVC
        driver.switch_to.frame(iframes[2])
        cvc_field = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cvc'], input[placeholder*='CVC'], input[data-elements-stable-field-name='cardCvc']"))
        )
        cvc_field.clear()
        cvc_field.send_keys(card_cvc)
        driver.switch_to.default_content()
        logging.info("✅ CVC saisi")

        # Submit payment
        submit_btn = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        submit_btn.click()
        logging.info("✅ Paiement soumis")

        try:
            WebDriverWait(driver, 14).until(
                lambda d: "confirmation" in d.current_url.lower() or "success" in d.current_url.lower()
            )
            logging.info("🎉 RÉSERVATION CONFIRMÉE!")
            return True
        except:
            time.sleep(3)
            page_source = driver.page_source.lower()
            if any(word in page_source for word in ["confirmed", "success", "booked", "reserved", "confirmation"]):
                logging.info("🎉 RÉSERVATION PROBABLEMENT CONFIRMÉE!")
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

    base_urls = [
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=guest",
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate?date={date}",
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/Calendar?date={date}",
        "https://clubspark.lta.org.uk/SouthwarkPark/Booking"
    ]

    url_success = False
    for url in base_urls:
        try:
            logging.info(f"🌐 Essai navigation: {url}")
            driver.get(url)
            time.sleep(3)
            if "booking" in driver.current_url.lower() or "calendar" in driver.current_url.lower():
                url_success = True
                logging.info(f"✅ URL réussie: {url}")
                break
        except:
            continue

    if not url_success:
        logging.error("❌ Impossible de naviguer vers la page de réservation")
        exit(1)

    take_screenshot("initial_page")

    login_success = login_first(username, password)
    is_logged_in = login_success

    if login_success:
        logging.info("✅ Login réussi - Mode optimisé activé")
        driver.get(base_urls[0])
        time.sleep(2)
    else:
        logging.warning("⚠️ Login échoué, on continue...")

    attempt = 0
    max_attempts = 300 if is_logged_in else 10

    while attempt < max_attempts and (time.time() - start_time) < max_duration:
        attempt += 1
        elapsed = int(time.time() - start_time)
        
        if attempt % 10 == 0:  # Log less frequently
            logging.info(f"🔄 Tentative {attempt}/{max_attempts} (temps: {elapsed}s)")

        if find_and_book_slot():
            logging.info("🎉 RÉSERVATION RÉUSSIE!")
            break
        else:
            if attempt < max_attempts and (time.time() - start_time) < max_duration - 10:
                refresh_delay = 0.2 if is_logged_in else 1.0  # Faster refresh
                time.sleep(refresh_delay)
                driver.refresh()
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
