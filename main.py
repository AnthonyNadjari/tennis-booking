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
import random

# --- LOGGING CONFIGURATION (your style) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'booking_{os.getpid()}.log'),
        logging.StreamHandler()
    ]
)

# --- CHROME OPTIONS ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/126.0",
    "Mozilla/5.0 (Linux; Android 14; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
]

def get_chrome_options():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # Randomize user-agent for stealth
    ua = random.choice(USER_AGENTS)
    options.add_argument(f"user-agent={ua}")
    return options

def take_screenshot(driver, name):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{name}_{os.getpid()}_{timestamp}.png"
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
            sign_in_link = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in') or contains(@href, 'login')]"))
            )
            sign_in_link.click()
            logging.info("✅ Cliqué sur Sign in")
            time.sleep(2)  # Give time for modal to appear
        except Exception as e:
            logging.warning(f"Sign in non trouvé: {e}")

        # Step 2: Wait for the login modal/fields to show up
        try:
            username_field = WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Username' or @name='username' or @id='username']"))
            )
            time.sleep(0.5)
            username_field.clear()
            username_field.send_keys(username)
            logging.info("✅ Username saisi")

            password_field = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Password' or @name='password' or @id='password' or @type='password']"))
            )
            time.sleep(0.3)
            password_field.clear()
            password_field.send_keys(password)
            logging.info("✅ Password saisi")

            # Submit login
            submit_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Login') or @type='submit']"))
            )
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
def wait_for_page_load(driver):
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.book-interval"))
        )
        time.sleep(0.1)
        logging.info("✅ Page de réservation chargée")
        return True
    except TimeoutException:
        logging.warning("⚠️ Timeout lors du chargement de la page")
        return False

def find_and_book_slot_all_courts(driver, total_minutes, hour_str, court_filter=None):
    try:
        # Accept cookies first if present
        try:
            cookie_btn = driver.find_element(By.CLASS_NAME, "osano-cm-accept-all")
            cookie_btn.click()
            time.sleep(0.1)
        except:
            pass

        if not wait_for_page_load(driver):
            return False

        logging.info(f"🔍 Recherche créneaux à {hour_str} sur tous les courts...")

        # Filter for a specific court if court_filter is set
        if court_filter:
            xpath_query = f"//a[contains(@class,'book-interval') and contains(@class,'not-booked') and contains(@data-test-id, '|{total_minutes}') and contains(@data-test-id, '{court_filter}') and not(contains(@class, 'disabled'))]"
        else:
            xpath_query = f"//a[contains(@class,'book-interval') and contains(@class,'not-booked') and contains(@data-test-id, '|{total_minutes}') and not(contains(@class, 'disabled'))]"

        slots = driver.find_elements(By.XPATH, xpath_query)

        if slots:
            for slot in slots:
                try:
                    logging.info("🎯 SLOT DISPONIBLE, tentative de réservation...")
                    slot.click()
                    if complete_booking_process(driver):
                        return True
                except ElementClickInterceptedException:
                    logging.warning("⚠️ Slot click intercepté, tentative suivante.")
                    continue

        logging.debug(f"Aucun slot trouvé pour {hour_str} (court_filter={court_filter})")
        return False

    except Exception as e:
        logging.error(f"❌ Erreur recherche slot: {e}")
        return False

def complete_booking_process(driver):
    try:
        try:
            duration_select = driver.find_element(By.ID, "booking-duration")
            Select(duration_select).select_by_index(1)
            logging.info("✅ Durée sélectionnée (booking-duration)")
        except:
            try:
                select2_dropdown = driver.find_element(By.CSS_SELECTOR, ".select2-selection, .select2-selection--single")
                select2_dropdown.click()
                options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
                if len(options) >= 2:
                    options[1].click()
                    logging.info("✅ Durée sélectionnée (select2)")
            except:
                pass

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

        try:
            pay_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, "paynow"))
            )
            pay_btn.click()
            logging.info("✅ Pay Now cliqué")
        except:
            logging.error("❌ Bouton Pay Now non trouvé")
            return False

        return handle_stripe_payment(driver)

    except Exception as e:
        logging.error(f"❌ Erreur booking: {e}")
        return False

def handle_stripe_payment(driver):
    try:
        logging.info("💳 Traitement paiement Stripe...")
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
        card_field.send_keys(os.environ.get('CARD_NUMBER', '5555555555554444'))
        driver.switch_to.default_content()
        logging.info("✅ Numéro carte saisi")

        # Expiry date
        driver.switch_to.frame(iframes[1])
        expiry_field = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='exp-date'], input[placeholder*='MM'], input[data-elements-stable-field-name='cardExpiry']"))
        )
        expiry_field.clear()
        expiry_field.send_keys(os.environ.get('CARD_EXPIRY', '04/30'))
        driver.switch_to.default_content()
        logging.info("✅ Date expiration saisie")

        # CVC
        driver.switch_to.frame(iframes[2])
        cvc_field = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cvc'], input[placeholder*='CVC'], input[data-elements-stable-field-name='cardCvc']"))
        )
        cvc_field.clear()
        cvc_field.send_keys(os.environ.get('CARD_CVC', '666'))
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
        take_screenshot(driver, "stripe_error")
        return False

def main():
    account_number = os.environ.get('ACCOUNT', '1')
    username = os.environ.get('TENNIS_USERNAME2') if account_number == '2' else os.environ.get('TENNIS_USERNAME')
    password = os.environ.get('TENNIS_PASSWORD')
    date = os.environ.get('BOOKING_DATE', '2025-06-16')
    hour = int(os.environ.get('BOOKING_HOUR', '7'))
    minutes = int(os.environ.get('BOOKING_MINUTES', '0'))
    total_minutes = (hour * 60) + minutes
    hour_str = f"{hour:02d}:{minutes:02d}"
    court_filter = os.environ.get('COURT_FILTER', None)

    base_urls = [
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=guest",
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate?date={date}",
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/Calendar?date={date}",
        "https://clubspark.lta.org.uk/SouthwarkPark/Booking"
    ]

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=get_chrome_options())
        driver.set_window_size(1920, 1080)
        url_success = False
        for url in base_urls:
            try:
                logging.info(f"🌐 Essai navigation: {url}")
                driver.get(url)
                time.sleep(1)
                if "booking" in driver.current_url.lower() or "calendar" in driver.current_url.lower():
                    url_success = True
                    logging.info(f"✅ URL réussie: {url}")
                    break
            except:
                continue
        if not url_success:
            logging.error("❌ Impossible de naviguer vers la page de réservation")
            return

        if not login_first(driver, username, password):
            logging.error("❌ Login échoué")
            return
        driver.get(base_urls[0])
        time.sleep(1)

        # Main booking loop (ultra-fast)
        start_time = time.time()
        max_duration = int(os.environ.get("MAX_DURATION", "1800"))  # seconds
        attempt = 0
        while True:
            attempt += 1
            elapsed = int(time.time() - start_time)
            logging.info(f"🔄 Tentative {attempt} (temps: {elapsed}s)")
            if find_and_book_slot_all_courts(driver, total_minutes, hour_str, court_filter):
                logging.info("🎉 RÉSERVATION RÉUSSIE!")
                break
            if max_duration and elapsed > max_duration:
                logging.warning("⏳ Durée maximale atteinte, arrêt du script.")
                break
            time.sleep(random.uniform(0.05, 0.25))
            driver.refresh()

        total_time = int(time.time() - start_time)
        logging.info(f"✅ Script terminé en {total_time}s après {attempt} tentatives")

    except Exception as e:
        logging.error(f"❌ Erreur critique: {e}")
        take_screenshot(driver, "critical_error")
    finally:
        if driver:
            driver.quit()
            logging.info("🏁 Driver fermé")

if __name__ == "__main__":
    main()
