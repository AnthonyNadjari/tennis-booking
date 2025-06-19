from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
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
        logging.FileHandler('tennis_booking.log'),
        logging.StreamHandler()
    ]
)
# Configuration Chrome
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Remove this line if you want to see the browser
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.page_load_strategy = 'eager'
# Environment Variables Configuration
username = os.environ.get('TENNIS_USERNAME')  # Default fallback
password = os.environ.get('TENNIS_PASSWORD')  # Default fallback
card_number = os.environ.get('CARD_NUMBER')
card_expiry = os.environ.get('CARD_EXPIRY')
card_cvc = os.environ.get('CARD_CVC')
booking_day = os.environ.get('BOOKING_DATE')
booking_hour = int(os.environ.get('BOOKING_HOUR'))  # 7 PM = 19 in 24h format
booking_minutes = int(os.environ.get('BOOKING_MINUTES'))

# Validation
if not username or not password:
    logging.error("❌ Username or password not defined!")
    exit(1)

# Calculate target time
target_time_minutes = booking_hour * 60 + booking_minutes
hour_str = f"{booking_hour:02d}:{booking_minutes:02d}"

logging.info(f"🎾 Tennis booking for day {booking_day} at {hour_str}")
logging.info(f"⏰ Target time in minutes: {target_time_minutes}")
logging.info(f"👤 Username: {username}")
# Initialize driver
driver = None

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_size(1920, 1080)
    wait = WebDriverWait(driver, 10)
    logging.info("✅ Driver initialized")
except Exception as e:
    logging.error(f"❌ Driver error: {e}")
    exit(1)
def take_screenshot(name):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{name}_{timestamp}.png"
        driver.save_screenshot(filename)
        logging.info(f"📸 Screenshot saved: {filename}")
    except Exception as e:
        logging.error(f"Screenshot error: {e}")

def enter_data(xpath, keys):
    try:
        element = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
        element.clear()
        element.send_keys(keys, Keys.RETURN)
        return True
    except Exception as e:
        logging.error(f"Error entering data in {xpath}: {e}")
        return False

def click_on(xpath):
    try:
        element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        element.click()
        return True
    except Exception as e:
        logging.error(f"Error clicking {xpath}: {e}")
        return False


def login_process():
    try:
        logging.info("🔐 Starting login process...")
        
        # Navigate to login page (exact same URL as original)
        driver.get("https://clubspark.lta.org.uk/SouthwarkPark/Account/SignIn?returnUrl=https%3a%2f%2fclubspark.lta.org.uk%2fSouthwarkPark%2fBooking%2fBookByDate")
        
        # Click login button (exact same XPath)
        if not click_on('/html/body/div[3]/div[1]/div[2]/div[1]/div[2]/form/button'):
            logging.error("❌ Could not click login button")
            return False
            
        # Enter username (exact same XPath and method)
        if not enter_data('//*[@id="154:0"]', username):
            logging.error("❌ Could not enter username")
            return False
            
        # Enter password (exact same XPath and method)
        if not enter_data('//*[@id="input-2"]', password):
            logging.error("❌ Could not enter password")
            return False
            
        logging.info("✅ Login completed")
        time.sleep(2)  # Same wait time as original
        return True
        
    except Exception as e:
        logging.error(f"❌ Login error: {e}")
        take_screenshot("login_error")
        return False


def select_date():
    try:
        booking_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={booking_day}&role=member"
        logging.info(f"🌐 Navigation vers: {booking_url}")
        driver.get(booking_url)
        time.sleep(3)
        logging.info("✅ Date selected via URL")
        return True
        
    except Exception as e:
        logging.error(f"❌ Date selection error: {e}")
        return False


def find_and_book_slot():
    try:
        logging.info(f"🔍 Looking for slot at {hour_str} ({target_time_minutes} minutes)")
        
        # Retry logic - max 5 minutes
        start_time = time.time()
        max_duration = 5 * 60  # 5 minutes in seconds
        attempt = 0
        
        while time.time() - start_time < max_duration:
            attempt += 1
            elapsed = int(time.time() - start_time)
            remaining_time = int(max_duration - (time.time() - start_time))
            logging.info(f"🔄 Attempt {attempt} (elapsed: {elapsed}s, remaining: {remaining_time}s)")
            
            try:
                # Wait for page to load - if no slots, this will timeout and we'll refresh
                wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'a.book-interval')))
                
                # Try direct XPath targeting first
                xpath_query = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{target_time_minutes}')]"
                
                try:
                    target_slot = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, xpath_query))
                    )
                    logging.info(f"🎯 SLOT FOUND DIRECTLY at {hour_str}!")
                    target_slot.click()
                    logging.info("✅ Clicked!")
                    take_screenshot("the slot is found and we clicked ")
                    return True
                    
                except TimeoutException:
                    logging.info("⚠️ Direct search failed, trying fallback method...")
                    
                    # Fallback: search through all available slots
                    booking_links = driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked")
                    
                    for link in booking_links:
                        data_test_id = link.get_attribute('data-test-id') or ""
                        
                        if '|' in data_test_id:
                            parts = data_test_id.split('|')
                            if len(parts) >= 3:
                                try:
                                    slot_time = int(parts[2])
                                    if slot_time == target_time_minutes:
                                        logging.info(f"🎯 SLOT FOUND at {hour_str}!")
                                        link.click()
                                        return True
                                except (ValueError, IndexError):
                                    continue
                    
                    # Target slot not found in this attempt
                    logging.info(f"❌ Target slot {hour_str} not found in current slots")
                    
            except TimeoutException:
                # No booking intervals found at all
                logging.info("⚠️ No booking slots available on page")
            
            # Check if we still have time to continue
            if time.time() - start_time < max_duration - 2:  # Leave 2 seconds buffer
                logging.info("🔄 Refreshing page to check for new slots...")
                driver.refresh()
                time.sleep(1)  # Short wait between refreshes
            else:
                logging.info("⏰ Time limit almost reached, stopping search")
                break
        
        total_elapsed = int(time.time() - start_time)
        logging.error(f"❌ No slot found for {hour_str} after {total_elapsed}s and {attempt} attempts")
        return False
        
    except Exception as e:
        logging.error(f"❌ Slot booking error: {e}")
        take_screenshot("slot_booking_error")
        return False


def complete_booking():
    try:
        logging.info("💳 Completing booking process...")
        time.sleep(2)
        
        # Step 1: Handle duration selection more robustly
        duration_selected = False
        
        try:
            # First, try to click the dropdown to open it
            dropdown_selectors = [
                '/html/body/div[8]/div/div/div/div[1]/form/div[1]/div[1]/div[2]/div/div/div/span',
                '//span[contains(@class, "select2-selection")]',
                '//*[contains(@class, "select2-selection--single")]'
            ]
            
            dropdown_opened = False
            for selector in dropdown_selectors:
                try:
                    element = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    element.click()
                    dropdown_opened = True
                    logging.info("✅ Dropdown opened")
                    time.sleep(1)
                    break
                except:
                    continue
            
            if dropdown_opened:
                # Wait for dropdown options to appear and try multiple selectors
                option_selectors = [
                    '/html/body/span/span/span[2]/ul/li[2]',
                    '//li[contains(@class, "select2-results__option")][2]',
                    '//ul[contains(@class, "select2-results")]//li[2]',
                    '//li[@role="option"][2]',
                    '//span[contains(@class, "select2-results")]//li[2]'
                ]
                
                # Wait for options to be visible
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".select2-results__option"))
                    )
                except:
                    pass
                
                for selector in option_selectors:
                    try:
                        # Find all matching elements
                        elements = driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed():
                                # Try JavaScript click if regular click fails
                                try:
                                    element.click()
                                    duration_selected = True
                                    logging.info("✅ Duration selected")
                                    break
                                except:
                                    # Try JavaScript click as fallback
                                    driver.execute_script("arguments[0].click();", element)
                                    duration_selected = True
                                    logging.info("✅ Duration selected (JS click)")
                                    break
                        if duration_selected:
                            break
                    except:
                        continue
            
            # Alternative: Try native select element
            if not duration_selected:
                try:
                    from selenium.webdriver.support.ui import Select
                    select_element = driver.find_element(By.ID, "booking-duration")
                    select = Select(select_element)
                    select.select_by_index(1)
                    duration_selected = True
                    logging.info("✅ Duration selected (native select)")
                except:
                    pass
                    
        except Exception as e:
            logging.warning(f"⚠️ Duration selection error: {e}")
        
        if not duration_selected:
            logging.warning("⚠️ Could not select duration, continuing anyway...")
        
        time.sleep(2)
        
        # Step 2: Submit booking
        submit_selectors = [
            '//*[@id="submit-booking"]',
            '//button[contains(text(), "Continue")]',
            '//button[contains(text(), "Submit")]',
            '//input[@type="submit"]',
            '//button[@type="submit"]'
        ]
        
        submit_clicked = False
        for selector in submit_selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                element.click()
                submit_clicked = True
                logging.info("✅ Booking submitted")
                break
            except:
                continue
        
        if not submit_clicked:
            logging.error("❌ Could not submit booking")
            take_screenshot("submit_booking_error")
            return False
        
        time.sleep(3)
        
        # Step 3: Handle Pay Now button
        pay_selectors = [
            '//*[@id="paynow"]',
            '//button[contains(text(), "Pay now")]',
            '//button[contains(text(), "Pay Now")]',
            '//input[@value="Pay now"]',
            '//a[contains(text(), "Pay now")]'
        ]
        
        pay_clicked = False
        for selector in pay_selectors:
            try:
                element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                element.click()
                pay_clicked = True
                logging.info("✅ Pay Now clicked")
                break
            except:
                continue
        
        if not pay_clicked:
            logging.error("❌ Could not click Pay Now")
            take_screenshot("pay_now_error")
            return False
        
        time.sleep(2)
        
        # Step 4: Handle payment form
        return handle_payment_form()
        
    except Exception as e:
        logging.error(f"❌ Booking completion error: {e}")
        take_screenshot("booking_completion_error")
        return False

def handle_payment_form():
    try:
        logging.info("💳 Filling payment form...")
        
        # Check if payment form exists
        payment_fields = [
            ('//*[@id="cs-stripe-elements-card-number"]/div/iframe', card_number),
            ('//*[@id="cs-stripe-elements-card-expiry"]/div/iframe', card_expiry),
            ('//*[@id="cs-stripe-elements-card-cvc"]/div/iframe', card_cvc)
        ]
        
        for xpath, value in payment_fields:
            # Clear and fill each field multiple times
            for _ in range(3):
                enter_data(xpath, '')
            if not enter_data(xpath, value):
                logging.warning(f"⚠️ Could not fill payment field: {xpath}")
        
        # Submit payment
        submit_selectors = [
            '//*[@id="cs-stripe-elements-submit-button"]',
            '//button[contains(text(), "Pay")]',
            '//input[@type="submit"]'
        ]
        
        for selector in submit_selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                element.click()
                logging.info("✅ Payment submitted")
                time.sleep(5)
                return True
            except:
                continue
        
        logging.error("❌ Could not submit payment")
        return False
        
    except Exception as e:
        logging.error(f"❌ Payment form error: {e}")
        return False

# Main execution
try:
    start_time = time.time()

    # Login
    if not login_process():
        logging.error("❌ Login failed")
        exit(1)

    # Select date
    if not select_date():
        logging.error("❌ Date selection failed")
        exit(1)

    # Find and book slot
    if not find_and_book_slot():
        logging.error("❌ Slot booking failed")
        exit(1)

    # Complete booking
    if not complete_booking():
        logging.error("❌ Booking completion failed")
        exit(1)

    total_time = int(time.time() - start_time)
    logging.info(f"🎉 Booking process completed successfully in {total_time}s!")

except Exception as e:
    logging.error(f"❌ Critical error: {e}")
    if driver:
        take_screenshot("critical_error")
finally:
    if driver:
        driver.quit()
        logging.info("🏁 Driver closed")