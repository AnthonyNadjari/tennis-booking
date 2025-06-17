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
        logging.info(f"📸 Screenshot sauvegardé: {filename}")
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
            sign_in_link = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in') or contains(@href, 'login')]"))
            )
            sign_in_link.click()
            logging.info("✅ Cliqué sur Sign in")
            time.sleep(0.5)
        except Exception as e:
            logging.warning(f"Sign in non trouvé: {e}")

        # Step 2: Click Login button
        try:
            login_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Log in')]"))
            )
            login_btn.click()
            logging.info("✅ Cliqué sur Login")
            time.sleep(0.5)
        except Exception as e:
            logging.warning(f"Login button non trouvé: {e}")

        # Step 3: Fill credentials
        try:
            username_field = WebDriverWait(driver, 5).until(
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

            time.sleep(1)
            return True

        except Exception as e:
            logging.error(f"Erreur saisie credentials: {e}")
            return False

    except Exception as e:
        logging.error(f"❌ Erreur login: {e}")
        take_screenshot("login_error")
        return False

def wait_for_page_load():
    """Wait for the booking page to fully load - OPTIMIZED FOR SPEED"""
    try:
        # Just wait for the booking links to appear - no need for other checks
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.book-interval"))
        )

        # Minimal wait for dynamic content
        time.sleep(0.3)

        logging.info("✅ Page de réservation chargée")
        return True
    except TimeoutException:
        logging.warning("⚠️ Timeout lors du chargement de la page")
        return False

def find_and_book_slot():
    try:
        # Accept cookies first - but don't wait if not there
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

        # ULTRA FAST METHOD: Direct XPath to find slot with our exact time
        target_time_minutes = hour * 60 + minutes

        # Use XPath to directly find the link with our target time in data-test-id
        xpath_query = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{target_time_minutes}')]"

        try:
            # Find the slot directly
            target_slot = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, xpath_query))
            )

            logging.info(f"🎯 SLOT TROUVÉ DIRECTEMENT à {hour_str}!")

            # Click immediately - no screenshot, no scroll
            try:
                target_slot.click()
                logging.info("✅ Cliqué!")
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", target_slot)
                logging.info("✅ Cliqué avec JavaScript!")

            time.sleep(0.8)  # Minimal wait
            return complete_booking_process()

        except TimeoutException:
            # Fallback to searching all slots if direct method fails
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
                                try:
                                    link.click()
                                    logging.info("✅ Cliqué!")
                                except ElementClickInterceptedException:
                                    driver.execute_script("arguments[0].click();", link)
                                    logging.info("✅ Cliqué avec JavaScript!")
                                time.sleep(0.8)
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
        # Minimal wait
        time.sleep(0.3)

        # Select duration quickly
        try:
            select2_dropdown = driver.find_element(By.CSS_SELECTOR, ".select2-selection, .select2-selection--single")
            select2_dropdown.click()
            time.sleep(0.1)

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

        time.sleep(0.2)

        # Click Continue - try the most common selector first
        try:
            continue_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]"))
            )
            continue_btn.click()
            logging.info("✅ Continue cliqué")
            time.sleep(0.5)
        except:
            # Quick fallback
            try:
                continue_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
                continue_btn.click()
                logging.info("✅ Continue cliqué (submit)")
                time.sleep(0.5)
            except:
                logging.error("❌ Bouton Continue non trouvé")
                return False

        # Click Pay Now - direct ID first
        try:
            pay_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.ID, "paynow"))
            )
            pay_btn.click()
            logging.info("✅ Pay Now cliqué")
            time.sleep(0.5)
        except:
            logging.error("❌ Bouton Pay Now non trouvé")
            return False

        # Handle Stripe payment
        return handle_stripe_payment()

    except Exception as e:
        logging.error(f"❌ Erreur booking: {e}")
        return False

def handle_stripe_payment():
    try:
        logging.info("💳 Traitement paiement Stripe...")

        # Wait for Stripe iframes to load with a shorter timeout
        iframes = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
        )
        logging.info(f"✅ {len(iframes)} iframes Stripe trouvées")

        if len(iframes) < 3:
            logging.error("❌ Pas assez d'iframes Stripe")
            return False

        # Card number
        driver.switch_to.frame(iframes[0])
        card_field = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cardnumber'], input[placeholder*='card'], input[data-elements-stable-field-name='cardNumber']"))
        )
        card_field.clear()
        card_field.send_keys(card_number)
        driver.switch_to.default_content()
        logging.info("✅ Numéro carte saisi")
        time.sleep(0.2)  # Minimal delay

        # Expiry date
        driver.switch_to.frame(iframes[1])
        expiry_field = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='exp-date'], input[placeholder*='MM'], input[data-elements-stable-field-name='cardExpiry']"))
        )
        expiry_field.clear()
        expiry_field.send_keys(card_expiry)
        driver.switch_to.default_content()
        logging.info("✅ Date expiration saisie")
        time.sleep(0.2)  # Minimal delay

        # CVC
        driver.switch_to.frame(iframes[2])
        cvc_field = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cvc'], input[placeholder*='CVC'], input[data-elements-stable-field-name='cardCvc']"))
        )
        cvc_field.clear()
        cvc_field.send_keys(card_cvc)
        driver.switch_to.default_content()
        logging.info("✅ CVC saisi")
        time.sleep(0.2)  # Minimal delay

        # Submit payment
        submit_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(0.3)
        submit_btn.click()
        logging.info("✅ Paiement soumis")

        # Wait for confirmation with a shorter timeout initially
        try:
            WebDriverWait(driver, 15).until(
                lambda d: "confirmation" in d.current_url.lower() or "success" in d.current_url.lower()
            )
            logging.info("🎉 RÉSERVATION CONFIRMÉE!")
            return True
        except:
            # Check for any success indicators on page with a shorter delay
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
        return False

# Main execution
try:
    start_time = time.time()
    max_duration = 300  # 5 minutes max

    # Navigate to booking page - try different URL formats
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
            time.sleep(2)

            # Check if we're on a booking page
            if "booking" in driver.current_url.lower() or "calendar" in driver.current_url.lower():
                url_success = True
                logging.info(f"✅ URL réussie: {url}")
                break
        except:
            continue

    if not url_success:
        logging.error("❌ Impossible de naviguer vers la page de réservation")
        exit(1)

    # Login first
    login_success = login_first(username, password)
    is_logged_in = login_success

    if login_success:
        logging.info("✅ Login réussi - Mode optimisé activé")
        # After login, navigate back to booking page
        driver.get(base_urls[0])
        time.sleep(2)
    else:
        logging.warning("⚠️ Login échoué, on continue...")

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
                # Ultra fast refresh for logged-in users
                refresh_delay = 0.3 if is_logged_in else 1.0
                time.sleep(refresh_delay)
                # Refresh the page
                driver.refresh()
                time.sleep(0.3)
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
