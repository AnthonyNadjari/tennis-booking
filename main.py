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

# Configuration Chrome pour GitHub Actions
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

# Récupération des variables d'environnement
username = os.environ.get('TENNIS_USERNAME')
password = os.environ.get('TENNIS_PASSWORD')
card_number = os.environ.get('CARD_NUMBER', '5354562794845156')
card_expiry = os.environ.get('CARD_EXPIRY', '04/30')
card_cvc = os.environ.get('CARD_CVC', '666')
date = os.environ.get('BOOKING_DATE', '2025-06-16')
hour = int(os.environ.get('BOOKING_HOUR', '10'))

# Vérification des credentials
if not username or not password:
    logging.error("❌ TENNIS_USERNAME ou TENNIS_PASSWORD non définis!")
    exit(1)

# Conversion de l'heure en minutes système (format utilisé par le site)
hour_system_minutes = hour * 60
hour_str = f"{hour:02d}:00"

logging.info(f"🎾 Démarrage de la réservation pour le {date} à {hour_str}")
logging.info(f"⏰ Heure système recherchée: {hour_system_minutes} minutes")
logging.info(f"👤 Utilisateur: {username[:2]}***{username[-2:] if len(username) > 4 else '***'}")

# Initialize the Chrome driver
try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_size(1920, 1080)
    logging.info("✅ Driver Chrome initialisé")
except Exception as e:
    logging.error(f"❌ Erreur initialisation driver: {e}")
    exit(1)


def take_screenshot(name):
    """Prend une capture d'écran pour debug"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{name}_{timestamp}.png"
        driver.save_screenshot(filename)
        logging.info(f"📸 Screenshot sauvegardé: {filename}")
    except Exception as e:
        logging.error(f"Erreur screenshot: {e}")


def login_first(username, password):
    try:
        # Vérifier si déjà connecté
        if "Sign in" not in driver.page_source:
            logging.info("✅ Déjà connecté!")
            return True

        sign_in_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in')]"))
        )
        sign_in_btn.click()
        time.sleep(0.5)

        login_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login')]"))
        )
        login_button.click()
        time.sleep(0.5)

        username_field = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Username']"))
        )
        username_field.clear()
        username_field.send_keys(username)

        password_field = driver.find_element(By.XPATH, "//input[@placeholder='Password']")
        password_field.clear()
        password_field.send_keys(password)

        final_login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
        final_login_btn.click()

        time.sleep(1)
        logging.info("✅ Login soumis!")
        return True

    except Exception as e:
        logging.error(f"❌ Échec du login: {e}")
        return False


def try_booking():
    try:
        # Accepter les cookies si nécessaire
        try:
            accept_all_btn = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "osano-cm-accept-all"))
            )
            accept_all_btn.click()
            logging.info("✅ Cookies acceptés")
            time.sleep(0.5)
        except Exception:
            pass

        # Recherche des créneaux disponibles avec l'heure exacte
        logging.info(f"🔍 Recherche des créneaux pour {hour_str} ({hour_system_minutes} minutes)...")
        
        # Stratégie 1: Chercher directement les liens de réservation avec data-test-id
        booking_links = driver.find_elements(By.CSS_SELECTOR, f'a[data-test-id*="|{date}|{hour_system_minutes}"]')
        logging.info(f"📊 Trouvé {len(booking_links)} liens directs avec data-test-id")
        
        for link in booking_links:
            try:
                if "not-booked" in link.get_attribute("class"):
                    link_text = link.text
                    logging.info(f"✅ Créneau disponible trouvé: {link_text}")
                    
                    # Scroller et cliquer
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(0.2)
                    
                    try:
                        link.click()
                    except:
                        driver.execute_script("arguments[0].click();", link)
                    
                    logging.info("✅ Cliqué sur le créneau")
                    time.sleep(1)
                    
                    return complete_booking()
                    
            except Exception as e:
                logging.warning(f"Erreur avec ce lien: {e}")
                continue
        
        # Stratégie 2: Chercher via les divs resource-interval
        intervals = driver.find_elements(By.CSS_SELECTOR, f'div[data-system-start-time="{hour_system_minutes}"]')
        logging.info(f"📊 Trouvé {len(intervals)} intervals pour {hour_str}")
        
        for interval in intervals:
            try:
                # Chercher le lien de réservation dans cet interval
                booking_link = interval.find_element(By.CSS_SELECTOR, 'a.book-interval.not-booked')
                link_text = booking_link.text
                
                if "£" in link_text:  # Vérifier qu'il y a un prix
                    logging.info(f"✅ Créneau disponible trouvé: {link_text}")
                    
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", booking_link)
                    time.sleep(0.2)
                    
                    try:
                        booking_link.click()
                    except:
                        driver.execute_script("arguments[0].click();", booking_link)
                    
                    logging.info("✅ Cliqué sur le créneau")
                    time.sleep(1)
                    
                    return complete_booking()
                    
            except Exception as e:
                logging.warning(f"Pas de lien disponible dans cet interval: {e}")
                continue
        
        # Stratégie 3: Chercher tous les créneaux disponibles et filtrer
        all_available = driver.find_elements(By.CSS_SELECTOR, 'a.book-interval.not-booked')
        logging.info(f"📊 Trouvé {len(all_available)} créneaux disponibles au total")
        
        for link in all_available:
            try:
                link_text = link.text
                test_id = link.get_attribute('data-test-id') or ""
                
                # Vérifier si c'est pour notre heure
                if f"|{hour_system_minutes}" in test_id or f"{hour_str}" in link_text:
                    logging.info(f"✅ Créneau trouvé: {link_text}")
                    
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(0.2)
                    
                    try:
                        link.click()
                    except:
                        driver.execute_script("arguments[0].click();", link)
                    
                    logging.info("✅ Cliqué sur le créneau")
                    time.sleep(1)
                    
                    return complete_booking()
                    
            except Exception as e:
                continue
        
        logging.warning("❌ Aucun créneau disponible trouvé")
        return False

    except Exception as e:
        logging.error(f"❌ Erreur dans try_booking: {e}")
        take_screenshot("booking_error")
        return False


def complete_booking():
    """Complete the booking process after clicking on a slot"""
    try:
        take_screenshot("after_slot_click")
        
        # Sélection de la durée si nécessaire
        try:
            # Chercher select2 ou select normal
            try:
                select2_selection = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".select2-selection"))
                )
                select2_selection.click()
                time.sleep(0.5)
                
                options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
                if len(options) >= 2:
                    options[1].click()
                logging.info("✅ Durée sélectionnée via Select2")
            except:
                try:
                    duration_select = driver.find_element(By.ID, "booking-duration")
                    Select(duration_select).select_by_index(1)
                    logging.info("✅ Durée sélectionnée")
                except:
                    logging.info("⚠️ Pas de sélection de durée nécessaire")
        except:
            pass
        
        # Continue
        try:
            continue_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]"))
            )
            continue_btn.click()
            logging.info("✅ Continue cliqué")
            time.sleep(1)
        except Exception as e:
            logging.error(f"Erreur Continue: {e}")
            return False
        
        # Pay now
        try:
            paynow_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, "paynow"))
            )
            paynow_btn.click()
            logging.info("✅ Pay now cliqué")
            time.sleep(2)
        except Exception as e:
            logging.error(f"Erreur Pay now: {e}")
            return False
        
        # Paiement Stripe
        try:
            logging.info("💳 Traitement du paiement...")
            
            iframes = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
            )
            
            # Numéro de carte
            driver.switch_to.frame(iframes[0])
            card_field = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cardnumber']"))
            )
            card_field.send_keys(card_number)
            driver.switch_to.default_content()
            
            # Date d'expiration
            driver.switch_to.frame(iframes[1])
            expiry_field = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='exp-date']"))
            )
            expiry_field.send_keys(card_expiry)
            driver.switch_to.default_content()
            
            # CVC
            driver.switch_to.frame(iframes[2])
            cvc_field = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cvc']"))
            )
            cvc_field.send_keys(card_cvc)
            driver.switch_to.default_content()
            
            # Soumettre
            pay_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
            )
            pay_button.click()
            
            # Attendre confirmation
            WebDriverWait(driver, 15).until(EC.url_contains("confirmation"))
            take_screenshot("confirmation")
            logging.info("🎉 RÉSERVATION CONFIRMÉE!")
            return True
            
        except Exception as e:
            logging.error(f"Erreur paiement: {e}")
            take_screenshot("payment_error")
            return False
            
    except Exception as e:
        logging.error(f"Erreur complete_booking: {e}")
        take_screenshot("complete_booking_error")
        return False


# Programme principal
try:
    start_time = time.time()
    max_duration = 300  # 5 minutes maximum
    
    url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=guest"
    logging.info(f"🌐 Navigation vers: {url}")
    driver.get(url)
    time.sleep(2)
    take_screenshot("initial_page")

    # Login
    if not login_first(username, password):
        logging.warning("⚠️ Login échoué, on continue quand même")
    
    # Naviguer vers la page de réservation
    if "BookByDate" not in driver.current_url:
        driver.get(url)
        time.sleep(2)

    # Boucle de tentatives (max 5 minutes)
    attempt = 0
    while time.time() - start_time < max_duration:
        attempt += 1
        elapsed = int(time.time() - start_time)
        logging.info(f"🔄 Tentative {attempt} (temps écoulé: {elapsed}s)")

        if try_booking():
            logging.info("🎉 RÉSERVATION RÉUSSIE!")
            break
        else:
            if time.time() - start_time < max_duration - 10:  # Au moins 10s restantes
                logging.info("⏳ Actualisation dans 1 seconde...")
                time.sleep(1)
                driver.refresh()
                time.sleep(1)
            else:
                logging.info("⏰ Temps limite atteint")
                break

    total_time = int(time.time() - start_time)
    if total_time >= max_duration:
        logging.warning(f"⏰ Temps limite de 5 minutes atteint après {attempt} tentatives")
    else:
        logging.info(f"✅ Script terminé en {total_time}s après {attempt} tentatives")

except Exception as e:
    logging.error(f"❌ Erreur critique: {e}")
    take_screenshot("critical_error")
finally:
    driver.quit()
    logging.info("🏁 Driver fermé")
