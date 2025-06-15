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
hour = int(os.environ.get('BOOKING_HOUR', '7'))

# Vérification des credentials
if not username or not password:
    logging.error("❌ TENNIS_USERNAME ou TENNIS_PASSWORD non définis!")
    exit(1)

# Format hour and next_hour with leading zeros
hour_str = f"{hour:02d}:00"
next_hour = f"{(hour + 1) % 24:02d}:00"
hour_str_minutes = str(hour * 60)

logging.info(f"🎾 Démarrage de la réservation pour le {date} à {hour_str}")
logging.info(f"👤 Utilisateur: {username[:2]}***{username[-2:] if len(username) > 4 else '***'}")

# Initialize the Chrome driver avec webdriver-manager
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

        logging.info("🔐 Étape 1: Clic sur Sign in...")
        sign_in_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in')]"))
        )
        sign_in_btn.click()
        time.sleep(1)

        logging.info("🔐 Étape 2: Clic sur Login button...")
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login')]"))
        )
        login_button.click()
        time.sleep(1)

        logging.info("📝 Étape 3: Saisie des identifiants...")
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Username']"))
        )
        username_field.clear()
        username_field.send_keys(username)

        password_field = driver.find_element(By.XPATH, "//input[@placeholder='Password']")
        password_field.clear()
        password_field.send_keys(password)

        final_login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
        final_login_btn.click()

        logging.info("✅ Login soumis!")
        # Attendre le chargement
        time.sleep(3)
        take_screenshot("after_login")
        
        # Continuer même si on n'est pas sûr du succès
        return True

    except Exception as e:
        logging.error(f"❌ Échec du login: {e}")
        take_screenshot("login_error")
        return False


def try_booking():
    try:
        # Accepter les cookies si nécessaire
        try:
            accept_all_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "osano-cm-accept-all"))
            )
            accept_all_btn.click()
            logging.info("✅ Cookies acceptés")
        except Exception:
            logging.info("Pas de bannière cookies")

        # Attendre que la page soit complètement chargée
        time.sleep(2)
        
        # Méthode 1: Chercher directement tous les liens de réservation disponibles
        logging.info(f"🔍 Recherche des créneaux disponibles à {hour_str}...")
        
        # D'abord essayer de trouver tous les liens de réservation
        all_booking_links = driver.find_elements(By.CSS_SELECTOR, 'a.book-interval.not-booked')
        logging.info(f"📊 Trouvé {len(all_booking_links)} créneaux disponibles au total")
        
        # Filtrer pour l'heure souhaitée
        for link in all_booking_links:
            try:
                # Vérifier si c'est pour la bonne heure
                link_text = link.text
                data_test_id = link.get_attribute('data-test-id')
                
                logging.info(f"🔍 Vérification du créneau: {link_text}")
                
                # Vérifier si c'est l'heure qu'on veut (10:00 dans ce cas)
                if hour_str in link_text and ("£3.60" in link_text or "£4.95" in link_text or "£3.50" in link_text):
                    logging.info(f"✅ Créneau trouvé pour {hour_str}: {link_text}")
                    
                    # Scroller jusqu'au lien
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(1)
                    
                    # Essayer de cliquer
                    try:
                        link.click()
                    except:
                        # Si le clic normal échoue, utiliser JavaScript
                        driver.execute_script("arguments[0].click();", link)
                    
                    logging.info("✅ Cliqué sur le créneau")
                    take_screenshot("after_slot_click")
                    
                    # Attendre que la page suivante charge
                    time.sleep(2)
                    
                    # Sélection de la durée
                    try:
                        logging.info("⏱️ Sélection de la durée...")
                        
                        # Chercher le select2 ou le select normal
                        try:
                            select2_selection = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, ".select2-selection"))
                            )
                            select2_selection.click()
                            time.sleep(1)
                            
                            # Sélectionner la deuxième option (1 heure)
                            options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
                            if len(options) >= 2:
                                options[1].click()
                            logging.info("✅ Durée sélectionnée via Select2")
                        except:
                            # Fallback avec select standard
                            try:
                                duration_select = driver.find_element(By.ID, "booking-duration")
                                Select(duration_select).select_by_index(1)
                                logging.info("✅ Durée sélectionnée via select standard")
                            except:
                                logging.warning("⚠️ Impossible de sélectionner la durée, on continue...")
                    except Exception as e:
                        logging.warning(f"Sélection durée échouée: {e}")
                    
                    # Continuer
                    try:
                        continue_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]"))
                        )
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_btn)
                        time.sleep(1)
                        continue_btn.click()
                        logging.info("✅ Clicked Continue")
                    except Exception as e:
                        logging.error(f"Erreur au clic Continue: {e}")
                        take_screenshot("continue_error")
                        continue
                    
                    take_screenshot("after_continue")
                    time.sleep(2)
                    
                    # Payer
                    try:
                        paynow_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.ID, "paynow"))
                        )
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", paynow_btn)
                        time.sleep(1)
                        paynow_btn.click()
                        logging.info("✅ Clicked Confirm and pay")
                    except Exception as e:
                        logging.error(f"Erreur au clic Pay: {e}")
                        take_screenshot("pay_error")
                        continue
                    
                    # Paiement Stripe
                    logging.info("💳 Paiement Stripe...")
                    time.sleep(3)  # Attendre que Stripe charge
                    take_screenshot("stripe_form")
                    
                    try:
                        # Attendre les iframes Stripe
                        iframes = WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
                        )
                        logging.info(f"✅ Trouvé {len(iframes)} iframes Stripe")
                        
                        # Numéro de carte
                        driver.switch_to.frame(iframes[0])
                        card_field = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cardnumber']"))
                        )
                        card_field.send_keys(card_number)
                        driver.switch_to.default_content()
                        logging.info("✅ Numéro de carte saisi")
                        
                        # Date d'expiration
                        driver.switch_to.frame(iframes[1])
                        expiry_field = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='exp-date']"))
                        )
                        expiry_field.send_keys(card_expiry)
                        driver.switch_to.default_content()
                        logging.info("✅ Date d'expiration saisie")
                        
                        # CVC
                        driver.switch_to.frame(iframes[2])
                        cvc_field = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cvc']"))
                        )
                        cvc_field.send_keys(card_cvc)
                        driver.switch_to.default_content()
                        logging.info("✅ CVC saisi")
                        
                        # Soumettre le paiement
                        pay_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
                        )
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pay_button)
                        time.sleep(1)
                        pay_button.click()
                        logging.info("✅ Paiement soumis!")
                        
                        # Attendre la confirmation
                        WebDriverWait(driver, 20).until(EC.url_contains("confirmation"))
                        take_screenshot("confirmation")
                        logging.info("🎉 RÉSERVATION CONFIRMÉE!")
                        return True
                        
                    except Exception as e:
                        logging.error(f"Erreur paiement Stripe: {e}")
                        take_screenshot("stripe_error")
                        continue
                    
            except Exception as e:
                logging.warning(f"Erreur avec ce créneau: {e}")
                continue
        
        # Méthode 2: Si aucun lien direct trouvé, chercher via les divs
        if len(all_booking_links) == 0:
            logging.info("🔍 Méthode alternative: recherche via les divs...")
            am_slots = driver.find_elements(By.CSS_SELECTOR, f'div[data-system-start-time="{hour_str_minutes}"]')
            logging.info(f"✅ Trouvé {len(am_slots)} divs pour {hour_str}")
            
            for i, slot in enumerate(am_slots):
                try:
                    # Chercher le lien dans le parent ou les éléments proches
                    parent = slot.find_element(By.XPATH, "..")
                    booking_link = parent.find_element(By.CSS_SELECTOR, 'a.book-interval.not-booked')
                    
                    if "£3.60" in booking_link.text or "£4.95" in booking_link.text:
                        logging.info(f"✅ Créneau trouvé via div: {booking_link.text}")
                        driver.execute_script("arguments[0].click();", booking_link)
                        # ... continuer avec le reste du processus
                        
                except Exception as e:
                    logging.warning(f"Div {i + 1} - pas de lien trouvé: {e}")
                    continue

    except Exception as e:
        logging.error(f"❌ Erreur générale dans try_booking: {e}")
        take_screenshot("booking_error")
    
    return False


# Programme principal
try:
    # Navigation vers la page
    url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=guest"
    logging.info(f"🌐 Navigation vers: {url}")
    driver.get(url)
    time.sleep(3)
    take_screenshot("initial_page")

    # Login
    if not login_first(username, password):
        logging.error("❌ Impossible de se connecter")
        # Continuer quand même au cas où
    
    # Essayer de naviguer directement si pas sur la bonne page
    if "BookByDate" not in driver.current_url:
        driver.get(url)
        time.sleep(3)

    # Essayer de réserver (max 20 tentatives)
    max_attempts = 20
    attempts = 0

    while attempts < max_attempts:
        logging.info(f"🔄 Tentative {attempts + 1}/{max_attempts}")

        if try_booking():
            logging.info("✅ RÉSERVATION RÉUSSIE!")
            break
        else:
            attempts += 1
            if attempts < max_attempts:
                logging.info(f"⏳ Pas de créneaux disponibles. Actualisation dans 3 secondes...")
                time.sleep(3)
                driver.refresh()
                time.sleep(2)

    if attempts >= max_attempts:
        logging.warning(f"⚠️ Aucun créneau trouvé après {max_attempts} tentatives")

except Exception as e:
    logging.error(f"❌ Erreur critique: {e}")
    take_screenshot("critical_error")
finally:
    driver.quit()
    logging.info("🏁 Script terminé")
