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

# Variables d'environnement (original code preserved)
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

# Calculate total minutes and format display (original code preserved)
total_minutes = (hour * 60) + minutes
hour_system_minutes = total_minutes
hour_str = f"{hour:02d}:{minutes:02d}"

logging.info(f"🎾 Réservation pour le {date} à {hour_str}")
logging.info(f"⏰ Minutes système: {hour_system_minutes}")
logging.info(f"👤 Compte: {account_number} ({'Principal' if account_number == '1' else 'Secondaire'})")
logging.info(f"📸 Les screenshots seront sauvegardés dans le répertoire courant")

# Initialize driver - GLOBAL VARIABLE (original code preserved)
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

# KEEP THE ORIGINAL LOGIN FUNCTION UNCHANGED
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
   """Optimized page load wait"""
   try:
       WebDriverWait(driver, 3).until(
           lambda d: d.find_elements(By.CSS_SELECTOR, "a.book-interval") and
               any("not-booked" in el.get_attribute("class") for el in d.find_elements(By.CSS_SELECTOR, "a.book-interval"))
       )
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
           time.sleep(0.2)
       except:
           pass

       if not wait_for_page_load():
           return False

       logging.info(f"🔍 Recherche créneaux à {hour_str}...")
       target_time_minutes = hour * 60 + minutes

       # Optimized XPath query with more precise matching
       xpath_query = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{target_time_minutes}|')]"

       try:
           # Find the slot directly with reduced timeout
           target_slot = WebDriverWait(driver, 1).until(
               EC.element_to_be_clickable((By.XPATH, xpath_query))
           )

           # Use JavaScript click for faster execution
           driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", target_slot)
           logging.info(f"🎯 SLOT TROUVÉ ET CLIQUÉ à {hour_str}!")

           time.sleep(0.8)  # Reduced from 1.5 to 0.8
           return complete_booking_process()

       except TimeoutException:
           # Skip the fallback method to save time
           logging.warning(f"⚠️ Aucun slot trouvé pour {hour_str}")
           return False

   except Exception as e:
       logging.error(f"❌ Erreur recherche slot: {e}")
       return False

def complete_booking_process():
   try:
       # Minimal wait
       time.sleep(0.2)  # Reduced from 0.5

       # Select duration quickly using JavaScript
       try:
           driver.execute_script("""
               var durationSelect = document.querySelector('#booking-duration');
               if (durationSelect) {
                   durationSelect.selectedIndex = 1;
                   // Trigger change event if needed
                   var event = new Event('change');
                   durationSelect.dispatchEvent(event);
               }
           """)

           # Alternative method if first fails
           try:
               duration_select = driver.find_element(By.ID, "booking-duration")
               Select(duration_select).select_by_index(1)
           except:
               pass

           logging.info("✅ Durée sélectionnée via JS")
           time.sleep(0.2)  # Reduced from 0.3

       except Exception as e:
           logging.warning(f"Erreur sélection durée: {e}")

       # Click Continue - use JavaScript click with faster wait
       try:
           continue_btn = WebDriverWait(driver, 2).until(
               EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue') or @type='submit']"))
           )
           driver.execute_script("arguments[0].click();", continue_btn)
           logging.info("✅ Continue cliqué via JS")
           time.sleep(0.5)  # Reduced from 1.0
       except Exception as e:
           logging.error(f"❌ Bouton Continue non trouvé: {e}")
           return False

       # Click Pay Now - use JavaScript click with shorter wait
       try:
           pay_btn = WebDriverWait(driver, 2).until(  # Reduced from 3 to 2
               EC.element_to_be_clickable((By.ID, "paynow"))
           )
           driver.execute_script("arguments[0].click();", pay_btn)
           logging.info("✅ Pay Now cliqué via JS")
           time.sleep(0.5)  # Reduced from 1.0
       except Exception as e:
           logging.error(f"❌ Bouton Pay Now non trouvé: {e}")
           return False

       # Handle Stripe payment with optimized function
       return handle_stripe_payment()

   except Exception as e:
       logging.error(f"❌ Erreur processus réservation: {e}")
       return False

def handle_stripe_payment():
   try:
       logging.info("💳 Traitement paiement Stripe (optimisé)...")

       # Wait for Stripe iframes with reduced timeout
       iframes = WebDriverWait(driver, 8).until(  # Reduced from 15 to 8
           EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
       )
       logging.info(f"✅ {len(iframes)} iframes Stripe trouvées")

       if len(iframes) < 3:
           logging.error("❌ Pas assez d'iframes Stripe")
           return False

       # Optimized iframe processing with JavaScript value setting
       for i, field_value in enumerate([card_number, card_expiry, card_cvc]):
           if i >= len(iframes):
               break
           driver.switch_to.frame(iframes[i])

           try:
               field = WebDriverWait(driver, 3).until(
                   EC.presence_of_element_located((By.CSS_SELECTOR, "input"))
               )
               # Use JavaScript to set value directly
               driver.execute_script(f"arguments[0].value = '{field_value}';", field)

               # Simulate input events
               driver.execute_script("""
                   arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                   arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
               """, field)

           except Exception as e:
               logging.warning(f"Erreur champ {i}: {e}")
               driver.switch_to.default_content()
               continue

           driver.switch_to.default_content()
           time.sleep(0.1)  # Minimal delay between fields

       # Submit payment with JS click and reduced wait
       try:
           submit_btn = WebDriverWait(driver, 5).until(
               EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
           )
           driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", submit_btn)
           logging.info("✅ Paiement soumis via JS")

           # More aggressive confirmation check
           try:
               WebDriverWait(driver, 15).until(  # Reduced from 30 to 15
                   lambda d: any(x in d.current_url.lower() for x in ["confirmation", "success"])
               )
               take_screenshot("confirmation")
               logging.info("🎉 RÉSERVATION CONFIRMÉE!")
               return True
           except:
               # Faster fallback confirmation check
               time.sleep(2)  # Reduced from 5 to 2
               page_source = driver.page_source.lower()
               if any(word in page_source for word in ["confirmed", "success", "booked", "reserved", "confirmation"]):
                   logging.info("🎉 RÉSERVATION PROBABLEMENT CONFIRMÉE!")
                   return True
               else:
                   logging.error("❌ Pas de confirmation trouvée")
                   return False

       except Exception as e:
           logging.error(f"❌ Erreur soumission paiement: {e}")
           return False

   except Exception as e:
       logging.error(f"❌ Erreur paiement Stripe: {e}")
       take_screenshot("stripe_error")
       return False

# Main execution with optimized retry loop but keeping login unchanged
try:
   start_time = time.time()
   max_duration = 300  # Keep original 5 minutes max

   # Keep original URL navigation code
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

   # Keep original login process exactly as is
   login_success = login_first(username, password)
   is_logged_in = login_success

   if login_success:
       logging.info("✅ Login réussi - Mode optimisé activé")
       # After login, navigate back to booking page (keep original)
       driver.get(base_urls[0])
       time.sleep(3)
   else:
       logging.warning("⚠️ Login échoué, on continue...")

   # Optimized retry loop
   attempt = 0
   max_attempts = 1000  # Increased from 300 to 1000 for more attempts
   refresh_delay = 0.5  # Start with 0.5 second delay
   consecutive_failures = 0

   while attempt < max_attempts and (time.time() - start_time) < max_duration:
       attempt += 1
       elapsed = round(time.time() - start_time, 1)

       if attempt % 10 == 0:  # Log every 10 attempts to reduce output
           logging.info(f"🔄 Tentative {attempt}/{max_attempts} (temps: {elapsed}s, délai: {refresh_delay}s)")

       success = find_and_book_slot()
       if success:
           logging.info("🎉 RÉSERVATION RÉUSSIE!")
           break
       else:
           consecutive_failures += 1

           # Adaptive delay strategy
           if consecutive_failures > 5:
               refresh_delay = min(refresh_delay * 1.1, 2.0)  # Slow down slightly if many failures
           else:
               refresh_delay = max(0.2, refresh_delay * 0.95)  # Speed up if getting results

           if attempt < max_attempts and (time.time() - start_time) < max_duration - 5:
               # Fast refresh using JavaScript instead of driver.refresh()
               driver.execute_script("location.reload();")
               time.sleep(refresh_delay)
           else:
               break

   total_time = round(time.time() - start_time, 1)
   logging.info(f"✅ Script terminé en {total_time}s après {attempt} tentatives")

except Exception as e:
   logging.error(f"❌ Erreur critique: {e}")
   if driver:
       take_screenshot("critical_error")
finally:
   if driver:
       driver.quit()
       logging.info("🏁 Driver fermé")
