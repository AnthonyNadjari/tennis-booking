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

# Configure minimal logging to reduce overhead
logging.basicConfig(
   level=logging.INFO,
   format='%(asctime)s - %(levelname)s - %(message)s',
   handlers=[
       logging.FileHandler('booking.log'),
       logging.StreamHandler()
   ]
)

# Optimized Chrome configuration
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument("--disable-extensions")
options.add_argument("--disable-notifications")
options.add_argument("--mute-audio")
options.add_argument("--disable-infobars")

# Environment configuration
account_number = os.environ.get('ACCOUNT', '1')
username = os.environ.get('TENNIS_USERNAME2') if account_number == '2' else os.environ.get('TENNIS_USERNAME')
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

# Timing configuration
total_minutes = (hour * 60) + minutes
hour_system_minutes = total_minutes
hour_str = f"{hour:02d}:{minutes:02d}"

logging.info(f"🎾 Réservation pour le {date} à {hour_str}")
logging.info(f"👤 Compte: {account_number} ({'Principal' if account_number == '1' else 'Secondaire'})")

# Initialize driver with optimized settings
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
       logging.debug(f"📸 Screenshot sauvegardé: {filename}")
   except Exception as e:
       logging.error(f"Erreur screenshot: {e}")

def login_first(username, password):
   try:
       # Fast check if already logged in
       if any(x in driver.page_source for x in ["My bookings", "Log out"]):
           logging.info("✅ Déjà connecté!")
           return True

       logging.info("🔐 Connexion en cours...")

       # Aggressive login process
       try:
           sign_in_link = WebDriverWait(driver, 3).until(
               EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'login') or contains(text(), 'Sign in')]"))
           )
           driver.execute_script("arguments[0].click();", sign_in_link)
           time.sleep(0.5)
       except:
           pass  # Might already be on login page

       # Quick credential filling
       try:
           username_field = WebDriverWait(driver, 3).until(
               EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username'], input#username"))
           )
           username_field.send_keys(username)

           password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
           password_field.send_keys(password)

           login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
           driver.execute_script("arguments[0].click();", login_btn)
           time.sleep(1)
           return True

       except Exception as e:
           logging.error(f"❌ Erreur login: {e}")
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
       return True
   except:
       return False

def find_and_book_slot():
   try:
       if not wait_for_page_load():
           return False

       target_time_minutes = hour * 60 + minutes

       # Ultra-fast slot finding and clicking
       slot_xpath = f"//a[contains(@class, 'book-interval') and contains(@class, 'not-booked') and contains(@data-test-id, '|{target_time_minutes}|')]"

       try:
           target_slot = WebDriverWait(driver, 1).until(
               EC.element_to_be_clickable((By.XPATH, slot_xpath))
           )
           driver.execute_script("arguments[0].click();", target_slot)
           time.sleep(0.7)
           return complete_booking_process()
       except TimeoutException:
           return False

   except Exception as e:
       logging.error(f"❌ Erreur recherche slot: {e}")
       return False

def complete_booking_process():
   try:
       time.sleep(0.2)  # Minimal wait

       # Fast duration selection via JS
       try:
           driver.execute_script("""
               var durationSelect = document.querySelector('#booking-duration, .select2-selection');
               if (durationSelect) {
                   if (durationSelect.tagName.toLowerCase() === 'select') {
                       durationSelect.selectedIndex = 1;
                   } else {
                       durationSelect.click();
                       setTimeout(function() {
                           var options = document.querySelectorAll('.select2-results__option');
                           if (options.length > 1) options[1].click();
                       }, 100);
                   }
               }
           """)
           time.sleep(0.3)
       except:
           pass

       # Fast Continue click via JS
       try:
           driver.execute_script("""
               var continueBtn = document.querySelector('button:not([disabled]):not([hidden]):not([style*="display:none"])');
               if (!continueBtn) continueBtn = document.querySelector("button[type='submit']");
               if (continueBtn) continueBtn.click();
           """)
           time.sleep(0.5)
       except:
           pass

       # Fast Pay Now click via JS
       try:
           pay_btn = WebDriverWait(driver, 2).until(
               EC.element_to_be_clickable((By.ID, "paynow"))
           )
           driver.execute_script("arguments[0].click();", pay_btn)
           time.sleep(0.5)
       except Exception as e:
           logging.error(f"❌ Erreur bouton pay: {e}")
           return False

       return handle_stripe_payment()

   except Exception as e:
       logging.error(f"❌ Erreur processus réservation: {e}")
       return False

def handle_stripe_payment():
   try:
       logging.info("💳 Traitement paiement Stripe (optimisé)...")

       # Fast Stripe iframe handling
       iframes = WebDriverWait(driver, 8).until(
           EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
       )

       if len(iframes) >= 3:
           # Process each iframe with minimal delay
           for i, field_value in enumerate([card_number, card_expiry, card_cvc]):
               if i >= len(iframes):
                   break
               driver.switch_to.frame(iframes[i])
               field = WebDriverWait(driver, 3).until(
                   EC.presence_of_element_located((By.CSS_SELECTOR, "input"))
               )
               driver.execute_script(f"arguments[0].value = '{field_value}';", field)
               driver.switch_to.default_content()
               time.sleep(0.1)  # Minimal delay between fields

           # Fast payment submission
           submit_btn = WebDriverWait(driver, 5).until(
               EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
           )
           driver.execute_script("arguments[0].click();", submit_btn)

           # Quick confirmation checks
           for _ in range(3):
               if any(x in driver.current_url.lower() for x in ["confirmation", "success"]):
                   return True
               time.sleep(1)

           page_source = driver.page_source.lower()
           if any(word in page_source for word in ["confirmed", "success", "booked", "reserved", "confirmation"]):
               return True

       return False

   except Exception as e:
       logging.error(f"❌ Erreur paiement: {e}")
       take_screenshot("payment_error")
       return False

# Main execution with aggressive strategy
try:
   start_time = time.time()
   max_duration = 240  # 4 minutes total runtime

   # Navigate to booking page
   booking_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=guest"
   driver.get(booking_url)
   time.sleep(2)

   # Login if needed
   login_success = login_first(username, password)
   if login_success:
       driver.get(booking_url)
       time.sleep(1.5)

   # Aggressive booking loop
   attempt = 0
   refresh_delay = 0.3  # Very short initial delay

   while (time.time() - start_time) < max_duration:
       attempt += 1
       if attempt % 10 == 0:
           elapsed = round(time.time() - start_time, 1)
           logging.info(f"🔄 Tentative {attempt} (temps: {elapsed}s)")

       if find_and_book_slot():
           elapsed = round(time.time() - start_time, 1)
           logging.info(f"🎉 RÉSERVATION RÉUSSIE en {elapsed} secondes!")
           break

       # Adaptive delay strategy
       if attempt < 100:
           time.sleep(max(0.1, refresh_delay * 0.95))  # Decrease delay
       else:
           time.sleep(refresh_delay)

       # Fast refresh
       driver.execute_script("location.reload();")

   total_time = round(time.time() - start_time, 1)
   logging.info(f"⏰ Script terminé après {total_time} secondes et {attempt} tentatives")

except Exception as e:
   logging.error(f"❌ Erreur critique: {e}")
finally:
   driver.quit()
