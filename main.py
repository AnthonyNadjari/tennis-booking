from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
import time
import logging
from datetime import datetime, timedelta


# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tennis_booking.log'),
        logging.StreamHandler()
    ]
)
# Environment Variables - keeping your working values as defaults
username = os.environ.get('TENNIS_USERNAME')
password = os.environ.get('TENNIS_PASSWORD')
card_number = os.environ.get('CARD_NUMBER')
card_expiry = os.environ.get('CARD_EXPIRY')
card_cvc = os.environ.get('CARD_CVC')

# Date handling - extract day from full date or use default
booking_date = os.environ.get('BOOKING_DATE')
if booking_date:
    day = booking_date.split('-')[2].lstrip('0') or '1'  # Extract day and remove leading zero
else:
    day = os.environ.get('BOOKING_DAY', '25')

hours = int(os.environ.get('BOOKING_HOUR', '14'))
minutes = int(os.environ.get('BOOKING_MINUTES', '0'))

logging.info(f"🎾 Tennis booking for day {day} at {hours:02d}:{minutes:02d}")
logging.info(f"👤 Username: {username}")
# Setup Chrome - adapted for GitHub Actions
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.page_load_strategy = 'eager'

# Use ChromeDriverManager for GitHub Actions, fallback to local path
try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
except:
    # Fallback for local development
    service = Service(executable_path=r'C:\Users\x01376312\Downloads\chromedriver.exe')
    driver = webdriver.Chrome(service=service, options=options)

wait = WebDriverWait(driver, 10)
logging.info("✅ Driver initialized")
def timer(t):
    target_time = datetime.strptime(t, "%H:%M").replace(
        year=datetime.now().year,
        month=datetime.now().month,
        day=datetime.now().day
    )
    now = datetime.now()
    wait_seconds = (target_time - now).total_seconds()
    if wait_seconds > 0:
        time.sleep(wait_seconds)

def enter_data(xpath, keys):
    wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
    driver.find_element(By.XPATH, xpath).send_keys(keys, Keys.RETURN)

def click_on(xpath):
    wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    driver.find_element(By.XPATH, xpath).click()

def take_screenshot(name):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{name}_{timestamp}.png"
        driver.save_screenshot(filename)
        logging.info(f"📸 Screenshot saved: {filename}")
    except Exception as e:
        logging.error(f"Screenshot error: {e}")


try:
    ## Login (EXACT SAME)
    logging.info("🔐 Starting login process...")
    driver.get(
        r"https://clubspark.lta.org.uk/SouthwarkPark/Account/SignIn?returnUrl=https%3a%2f%2fclubspark.lta.org.uk%2fSouthwarkPark%2fBooking%2fBookByDate")
    click_on('/html/body/div[3]/div[1]/div[2]/div[1]/div[2]/form/button')
    enter_data('//*[@id="154:0"]', username)
    enter_data('//*[@id="input-2"]', password)
    logging.info("✅ Login completed")

    ## Select date (EXACT SAME)
    logging.info(f"📅 Selecting day: {day}")
    click_on('//*[@id="book-by-date-view"]/div/div[1]/div/div[1]/button')
    dates = driver.find_elements(By.CSS_SELECTOR, 'td[data-handler="selectDay"]')
    for d in dates:
        if d.text == day:
            d.click()
            break
    logging.info("✅ Date selected")

    ### COURT FINDING WITH RETRY LOGIC (EXACT SAME) ###
    driver.refresh()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'a.book-interval')))

    # Calculate target time in minutes
    target_time_minutes = hours * 60 + minutes
    hour_str = f"{hours:02d}:{minutes:02d}"
    logging.info(f"🔍 Looking for slot at {hour_str} ({target_time_minutes} minutes)")

    # Retry logic - max 5 minutes
    start_time = time.time()
    max_duration = 5 * 60  # 5 minutes in seconds
    attempt = 0
    slot_found = False

    while time.time() - start_time < max_duration:
        attempt += 1
        elapsed = int(time.time() - start_time)
        logging.info(f"🔄 Attempt {attempt} (elapsed: {elapsed}s)")

        # Try direct XPath targeting first
        xpath_query = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{target_time_minutes}')]"

        try:
            target_slot = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, xpath_query))
            )
            logging.info(f"🎯 SLOT FOUND DIRECTLY at {hour_str}!")
            target_slot.click()
            logging.info("✅ Clicked!")
            slot_found = True
            break  # Exit the retry loop

        except:
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
                                slot_found = True
                                break
                        except:
                            continue

            if slot_found:
                break  # Exit the retry loop

            # If no slot found and still have time, refresh and try again
            remaining_time = max_duration - (time.time() - start_time)
            if remaining_time > 10:  # Only refresh if we have more than 10 seconds left
                logging.info(f"❌ No slot found, refreshing... ({int(remaining_time)}s remaining)")
                driver.refresh()
                time.sleep(0.5)  # Small delay between refreshes
                try:
                    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'a.book-interval')))
                except:
                    logging.info("⚠️ Page load timeout, continuing...")
            else:
                logging.info("⏰ Time limit reached, stopping search")
                break

    # Check if slot was found
    if not slot_found:
        logging.error(f"❌ No slot found for {hour_str} after 5 minutes")
        take_screenshot("no_slot_found")
        driver.quit()
        exit()

    # Booking completion (EXACT SAME)
    click_on('/html/body/div[8]/div/div/div/div[1]/form/div[1]/div[1]/div[2]/div/div/div/span')
    click_on('/html/body/span/span/span[2]/ul/li[2]')
    click_on('//*[@id="submit-booking"]')
    click_on('//*[@id="paynow"]')
    time.sleep(0.5)

    # Payment form (EXACT SAME)
    enter_data('//*[@id="cs-stripe-elements-card-number"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-number"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-number"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-number"]/div/iframe', card_number)
    enter_data('//*[@id="cs-stripe-elements-card-expiry"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-expiry"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-expiry"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-expiry"]/div/iframe', card_expiry)
    enter_data('//*[@id="cs-stripe-elements-card-cvc"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-cvc"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-cvc"]/div/iframe', '')
    enter_data('//*[@id="cs-stripe-elements-card-cvc"]/div/iframe', card_cvc)


    logging.info("💳 Attempting to submit payment...")
    click_on('//*[@id="cs-stripe-elements-submit-button"]')
    logging.info("✅ Payment button clicked successfully")
    
    # Wait and check what happens
    for i in range(10):  # Check for 10 seconds
        time.sleep(0.5)
        current_url = driver.current_url
        logging.info(f"⏰ Second {i + 1}: Current URL: {current_url}")
    
        # Check if we're on a success/confirmation page
        if "success" in current_url.lower() or "confirmation" in current_url.lower() or "thank" in current_url.lower():
            logging.info("🎉 Payment appears successful - on confirmation page!")
            break
    
        # Check if still on payment page
        if "payment" in current_url.lower() or "stripe" in current_url.lower():
            logging.info("⚠️ Still on payment page...")
    
        # Check page content for success messages
        page_source = driver.page_source.lower()
        if "booking confirmed" in page_source or "payment successful" in page_source:
            logging.info("🎉 Success message found on page!")
            time.sleep(5)
            break
    
    logging.info("🎉 Booking process completed!")



except Exception as e:
    logging.error(f"❌ Error occurred: {e}")
    take_screenshot("error")
finally:
    if driver:

    logging.info("✅ Browser closed")