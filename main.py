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
import threading
import queue
import concurrent.futures
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking.log'),
        logging.StreamHandler()
    ]
)

# Configuration Chrome - OPTIMIZED FOR SPEED
def get_chrome_options():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")  # Don't load images for speed
    options.add_argument("--disable-javascript")  # Will re-enable when needed
    options.add_argument("--aggressive-cache-discard")
    options.add_argument("--memory-pressure-off")
    options.add_argument("--max_old_space_size=4096")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # Disable CSS/JS for faster loading where possible
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2
    }
    options.add_experimental_option("prefs", prefs)
    return options

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

# Global variables for thread coordination
booking_success = threading.Event()
driver_pool = []
result_queue = queue.Queue()

def create_driver():
    """Create optimized driver instance"""
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=get_chrome_options())
        driver.set_window_size(1920, 1080)
        # Enable JavaScript for booking interactions
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        logging.error(f"❌ Erreur driver: {e}")
        return None

def take_screenshot(driver, name):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{name}_{timestamp}.png"
        driver.save_screenshot(filename)
        logging.info(f"📸 Screenshot sauvegardé: {filename}")
    except Exception as e:
        logging.error(f"Erreur screenshot: {e}")

def login_first(driver, username, password):
    """Same login logic as original - keeping it unchanged"""
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
        take_screenshot(driver, "login_error")
        return False

class FastBookingThread(threading.Thread):
    def __init__(self, thread_id, target_time_minutes, hour_str):
        super().__init__()
        self.thread_id = thread_id
        self.target_time_minutes = target_time_minutes
        self.hour_str = hour_str
        self.driver = None
        self.name = f"BookingThread-{thread_id}"
        
    def run(self):
        try:
            self.driver = create_driver()
            if not self.driver:
                return
                
            logging.info(f"🚀 Thread {self.thread_id} started")
            
            # Navigate to booking page
            base_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=guest"
            self.driver.get(base_url)
            time.sleep(2)
            
            # Login
            if not login_first(self.driver, username, password):
                logging.error(f"❌ Thread {self.thread_id}: Login failed")
                return
                
            # Navigate back to booking after login
            self.driver.get(base_url)
            time.sleep(1)
            
            # Main booking loop - ULTRA FAST
            attempt = 0
            while not booking_success.is_set() and attempt < 500:
                attempt += 1
                
                if attempt % 50 == 0:
                    logging.info(f"🔄 Thread {self.thread_id} - Attempt {attempt}")
                
                if self.try_book_slot():
                    booking_success.set()
                    result_queue.put(f"SUCCESS: Thread {self.thread_id}")
                    logging.info(f"🎉 Thread {self.thread_id} BOOKING SUCCESS!")
                    return
                
                # Ultra-fast refresh - no sleep between attempts
                self.driver.refresh()
                time.sleep(0.1)  # Minimal wait
                
        except Exception as e:
            logging.error(f"❌ Thread {self.thread_id} error: {e}")
        finally:
            if self.driver:
                self.driver.quit()
    
    def try_book_slot(self):
        try:
            # Accept cookies if present
            try:
                cookie_btn = self.driver.find_element(By.CLASS_NAME, "osano-cm-accept-all")
                cookie_btn.click()
            except:
                pass
            
            # Wait for page elements with minimal timeout
            try:
                WebDriverWait(self.driver, 1).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.book-interval"))
                )
            except:
                return False
            
            # SPEED OPTIMIZED: Find all courts simultaneously
            # Look for ANY available slot at target time across all courts
            xpath_queries = [
                f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{self.target_time_minutes}')]",
                f"//a[contains(@class, 'book-interval') and contains(@class, 'not-booked') and contains(@data-test-id, 'Court') and contains(@data-test-id, '|{self.target_time_minutes}')]"
            ]
            
            for xpath in xpath_queries:
                try:
                    available_slots = self.driver.find_elements(By.XPATH, xpath)
                    if available_slots:
                        # Get first available slot - ANY court is fine
                        slot = available_slots[0]
                        court_info = slot.get_attribute('data-test-id') or ""
                        
                        logging.info(f"🎯 Thread {self.thread_id}: SLOT FOUND - {court_info}")
                        
                        # INSTANT CLICK - no scroll, no wait
                        self.driver.execute_script("arguments[0].click();", slot)
                        
                        # Fast booking completion
                        return self.complete_booking_ultra_fast()
                        
                except Exception as e:
                    continue
            
            return False
            
        except Exception as e:
            return False
    
    def complete_booking_ultra_fast(self):
        try:
            # OPTIMIZED: Pre-click everything in rapid succession
            time.sleep(0.2)  # Minimal wait for page elements
            
            # Duration selection - try multiple methods simultaneously
            duration_set = False
            
            # Method 1: Select2 dropdown
            try:
                select2 = self.driver.find_element(By.CSS_SELECTOR, ".select2-selection")
                self.driver.execute_script("arguments[0].click();", select2)
                time.sleep(0.1)
                
                options = self.driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
                if len(options) >= 2:
                    self.driver.execute_script("arguments[0].click();", options[1])
                    duration_set = True
            except:
                pass
            
            # Method 2: Regular select
            if not duration_set:
                try:
                    duration_select = self.driver.find_element(By.ID, "booking-duration")
                    Select(duration_select).select_by_index(1)
                    duration_set = True
                except:
                    pass
            
            time.sleep(0.1)
            
            # Continue button - FORCE CLICK
            continue_clicked = False
            continue_selectors = [
                "//button[contains(text(), 'Continue')]",
                "//button[@type='submit']",
                "//input[@type='submit']"
            ]
            
            for selector in continue_selectors:
                try:
                    btn = self.driver.find_element(By.XPATH, selector)
                    self.driver.execute_script("arguments[0].click();", btn)
                    continue_clicked = True
                    break
                except:
                    continue
            
            if not continue_clicked:
                return False
            
            time.sleep(0.3)
            
            # Pay Now - IMMEDIATE EXECUTION
            try:
                pay_btn = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.ID, "paynow"))
                )
                self.driver.execute_script("arguments[0].click();", pay_btn)
                time.sleep(0.5)
            except:
                return False
            
            # ULTRA FAST STRIPE PAYMENT
            return self.handle_stripe_ultra_fast()
            
        except Exception as e:
            logging.error(f"❌ Thread {self.thread_id} booking completion error: {e}")
            return False
    
    def handle_stripe_ultra_fast(self):
        try:
            logging.info(f"💳 Thread {self.thread_id}: ULTRA FAST Stripe payment")
            
            # Wait for Stripe iframes - REDUCED TIMEOUT
            iframes = WebDriverWait(self.driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
            )
            
            if len(iframes) < 3:
                return False
            
            # PARALLEL FORM FILLING using JavaScript execution
            # This is much faster than switching frames
            
            # Card number
            self.driver.switch_to.frame(iframes[0])
            card_field = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input"))
            )
            # SPEED: Send all keys at once
            card_field.send_keys(card_number)
            self.driver.switch_to.default_content()
            
            # Expiry - IMMEDIATE
            self.driver.switch_to.frame(iframes[1])
            expiry_field = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input"))
            )
            expiry_field.send_keys(card_expiry)
            self.driver.switch_to.default_content()
            
            # CVC - IMMEDIATE
            self.driver.switch_to.frame(iframes[2])
            cvc_field = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input"))
            )
            cvc_field.send_keys(card_cvc)
            self.driver.switch_to.default_content()
            
            # INSTANT SUBMIT
            submit_btn = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.ID, "cs-stripe-elements-submit-button"))
            )
            self.driver.execute_script("arguments[0].click();", submit_btn)
            
            # Wait for confirmation - COMPETITIVE TIMEOUT
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda d: any(word in d.current_url.lower() for word in ["confirmation", "success"])
                )
                take_screenshot(self.driver, f"success_thread_{self.thread_id}")
                return True
            except:
                # Quick page check
                time.sleep(2)
                page_source = self.driver.page_source.lower()
                if any(word in page_source for word in ["confirmed", "success", "booked", "reserved"]):
                    return True
                return False
                
        except Exception as e:
            logging.error(f"❌ Thread {self.thread_id} Stripe error: {e}")
            return False

def main():
    try:
        start_time = time.time()
        
        logging.info(f"🚀 STARTING COMPETITIVE BOOKING BOT")
        logging.info(f"🎯 Target: {date} at {hour_str}")
        logging.info(f"⚡ Mode: ULTRA COMPETITIVE - Multi-threaded")
        
        # Create multiple threads for maximum speed
        # 4 threads = 1 per potential court + extras for speed
        num_threads = 6
        threads = []
        
        for i in range(num_threads):
            thread = FastBookingThread(i+1, hour_system_minutes, hour_str)
            threads.append(thread)
            thread.start()
            time.sleep(0.1)  # Stagger starts slightly
        
        # Wait for either success or timeout
        max_wait_time = 300  # 5 minutes
        start_wait = time.time()
        
        while not booking_success.is_set() and (time.time() - start_wait) < max_wait_time:
            time.sleep(0.5)
            
            # Check if any thread succeeded
            if not result_queue.empty():
                result = result_queue.get()
                logging.info(f"🎉 {result}")
                break
        
        # Signal all threads to stop
        booking_success.set()
        
        # Wait for all threads to finish
        for thread in threads:
            thread.join(timeout=5)
        
        total_time = int(time.time() - start_time)
        
        if not result_queue.empty():
            logging.info(f"🎉 BOOKING SUCCESSFUL in {total_time}s!")
        else:
            logging.info(f"⏱️ Booking attempt completed in {total_time}s - check results")
            
    except Exception as e:
        logging.error(f"❌ Main execution error: {e}")
    
    logging.info("🏁 Competitive booking bot finished")

if __name__ == "__main__":
    main()
