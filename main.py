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

# Configuration Chrome - OPTIMIZED FOR SPEED AND STRIPE COMPATIBILITY
def get_chrome_options():
    options = webdriver.ChromeOptions()
    # REMOVED --headless for better Stripe compatibility
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    # REMOVED --disable-javascript for Stripe compatibility
    options.add_argument("--aggressive-cache-discard")
    options.add_argument("--memory-pressure-off")
    options.add_argument("--max_old_space_size=4096")
    # Better automation detection evasion
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # Optimize but keep essential features for payment processing
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "profile.managed_default_content_settings.images": 2  # Still disable images for speed
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
        
        # Enhanced stealth mode for better compatibility
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        driver.execute_script("window.chrome = {runtime: {}}")
        
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
            take_screenshot(self.driver, f"stripe_start_thread_{self.thread_id}")
            
            # Wait for Stripe iframes with multiple strategies
            iframes = []
            for attempt in range(3):
                try:
                    iframes = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
                    )
                    if len(iframes) >= 3:
                        break
                    time.sleep(1)
                except:
                    time.sleep(1)
            
            if len(iframes) < 3:
                logging.error(f"❌ Thread {self.thread_id}: Only {len(iframes)} Stripe iframes found")
                return False
            
            logging.info(f"✅ Thread {self.thread_id}: Found {len(iframes)} Stripe iframes")
            
            # ENHANCED: Use ActionChains and better element waiting
            action = ActionChains(self.driver)
            
            # Card Number Field - ENHANCED INTERACTION
            try:
                self.driver.switch_to.frame(iframes[0])
                card_field = WebDriverWait(self.driver, 8).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='cardnumber'], input[placeholder*='card'], input[data-elements-stable-field-name='cardNumber'], input"))
                )
                
                # Multiple interaction methods
                self.driver.execute_script("arguments[0].focus();", card_field)
                card_field.clear()
                card_field.click()
                time.sleep(0.2)
                card_field.send_keys(card_number)
                
                # Verify input
                entered_value = card_field.get_attribute('value')
                logging.info(f"✅ Thread {self.thread_id}: Card number entered: {len(entered_value)} chars")
                
                self.driver.switch_to.default_content()
            except Exception as e:
                logging.error(f"❌ Thread {self.thread_id}: Card number error: {e}")
                self.driver.switch_to.default_content()
                return False
            
            # Expiry Date Field - ENHANCED INTERACTION
            try:
                self.driver.switch_to.frame(iframes[1])
                expiry_field = WebDriverWait(self.driver, 8).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='exp-date'], input[placeholder*='MM'], input[data-elements-stable-field-name='cardExpiry'], input"))
                )
                
                self.driver.execute_script("arguments[0].focus();", expiry_field)
                expiry_field.clear()
                expiry_field.click()
                time.sleep(0.2)
                expiry_field.send_keys(card_expiry)
                
                entered_value = expiry_field.get_attribute('value')
                logging.info(f"✅ Thread {self.thread_id}: Expiry entered: {entered_value}")
                
                self.driver.switch_to.default_content()
            except Exception as e:
                logging.error(f"❌ Thread {self.thread_id}: Expiry error: {e}")
                self.driver.switch_to.default_content()
                return False
            
            # CVC Field - ENHANCED INTERACTION
            try:
                self.driver.switch_to.frame(iframes[2])
                cvc_field = WebDriverWait(self.driver, 8).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='cvc'], input[placeholder*='CVC'], input[data-elements-stable-field-name='cardCvc'], input"))
                )
                
                self.driver.execute_script("arguments[0].focus();", cvc_field)
                cvc_field.clear()
                cvc_field.click()
                time.sleep(0.2)
                cvc_field.send_keys(card_cvc)
                
                entered_value = cvc_field.get_attribute('value')
                logging.info(f"✅ Thread {self.thread_id}: CVC entered: {len(entered_value)} chars")
                
                self.driver.switch_to.default_content()
            except Exception as e:
                logging.error(f"❌ Thread {self.thread_id}: CVC error: {e}")
                self.driver.switch_to.default_content()
                return False
            
            # Small wait for form validation
            time.sleep(0.5)
            
            # SUBMIT PAYMENT - MULTIPLE STRATEGIES
            submit_success = False
            submit_selectors = [
                "#cs-stripe-elements-submit-button",
                "button[type='submit']",
                ".SubmitButton",
                "button:contains('Pay')",
                "input[type='submit']"
            ]
            
            for selector in submit_selectors:
                try:
                    if selector.startswith("#"):
                        submit_btn = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.ID, selector[1:]))
                        )
                    else:
                        submit_btn = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    
                    # Multiple click strategies
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
                    time.sleep(0.2)
                    
                    # Try regular click first
                    try:
                        submit_btn.click()
                    except:
                        # Fallback to JavaScript click
                        self.driver.execute_script("arguments[0].click();", submit_btn)
                    
                    logging.info(f"✅ Thread {self.thread_id}: Payment submitted using {selector}")
                    submit_success = True
                    break
                    
                except Exception as e:
                    continue
            
            if not submit_success:
                logging.error(f"❌ Thread {self.thread_id}: Could not find submit button")
                take_screenshot(self.driver, f"no_submit_button_thread_{self.thread_id}")
                return False
            
            # Wait for confirmation with enhanced checking
            logging.info(f"⏳ Thread {self.thread_id}: Waiting for payment confirmation...")
            
            start_wait = time.time()
            while time.time() - start_wait < 20:  # 20 second timeout
                current_url = self.driver.current_url.lower()
                page_source = self.driver.page_source.lower()
                
                # Check URL first (fastest)
                if any(word in current_url for word in ["confirmation", "success", "complete", "thank"]):
                    logging.info(f"🎉 Thread {self.thread_id}: SUCCESS via URL change!")
                    take_screenshot(self.driver, f"success_thread_{self.thread_id}")
                    return True
                
                # Check page content
                if any(word in page_source for word in ["confirmed", "successful", "booked", "reserved", "thank you", "confirmation"]):
                    logging.info(f"🎉 Thread {self.thread_id}: SUCCESS via page content!")
                    take_screenshot(self.driver, f"success_content_thread_{self.thread_id}")
                    return True
                
                # Check for error messages
                if any(word in page_source for word in ["declined", "failed", "error", "invalid"]):
                    logging.error(f"❌ Thread {self.thread_id}: Payment error detected")
                    take_screenshot(self.driver, f"payment_error_thread_{self.thread_id}")
                    return False
                
                time.sleep(0.5)
            
            # Final check after timeout
            logging.warning(f"⚠️ Thread {self.thread_id}: Payment timeout - checking final state...")
            take_screenshot(self.driver, f"timeout_check_thread_{self.thread_id}")
            
            page_source = self.driver.page_source.lower()
            if any(word in page_source for word in ["confirmed", "successful", "booked", "reserved"]):
                logging.info(f"🎉 Thread {self.thread_id}: SUCCESS after timeout check!")
                return True
            
            return False
                
        except Exception as e:
            logging.error(f"❌ Thread {self.thread_id} Stripe error: {e}")
            take_screenshot(self.driver, f"stripe_error_thread_{self.thread_id}")
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
