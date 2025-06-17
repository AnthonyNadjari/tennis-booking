import multiprocessing
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(processName)s - %(levelname)s - %(message)s")

def main(court_index):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_size(1920, 1080)

    username = os.environ.get("TENNIS_USERNAME")
    password = os.environ.get("TENNIS_PASSWORD")
    date = os.environ.get("BOOKING_DATE", "2025-06-16")
    hour = int(os.environ.get("BOOKING_HOUR", "7"))
    minutes = int(os.environ.get("BOOKING_MINUTES", "0"))
    target_time_minutes = hour * 60 + minutes

    # Login function
    def login():
        driver.get(f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate?date={date}")
        time.sleep(2)
        try:
            sign_in_link = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in') or contains(@href, 'login')]"))
            )
            sign_in_link.click()
            time.sleep(1)
        except Exception:
            pass
        try:
            login_btn = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Log in')]"))
            )
            login_btn.click()
            time.sleep(1)
        except Exception:
            pass
        try:
            username_field = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, "//input[contains(@name,'username')]"))
            )
            username_field.clear()
            username_field.send_keys(username)
            password_field = driver.find_element(By.XPATH, "//input[contains(@name,'password')]")
            password_field.clear()
            password_field.send_keys(password)
            submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Login') or @type='submit']")
            submit_btn.click()
            time.sleep(3)
            return True
        except Exception as e:
            logging.error(f"Login failed: {e}")
            return False

    def find_slot():
        try:
            slots = driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked")
            if not slots:
                return None
            for link in slots:
                data_test_id = link.get_attribute('data-test-id') or ""
                # Print for debugging
                logging.info(f"Court {court_index}: Found slot data-test-id: {data_test_id}")
                # Try to parse the court index and time from data-test-id
                parts = data_test_id.split('|')
                if len(parts) >= 3:
                    try:
                        slot_court = int(parts[1])
                        slot_time = int(parts[2])
                        if slot_court == court_index and slot_time == target_time_minutes:
                            return link
                    except Exception:
                        continue
            return None
        except Exception as e:
            logging.error(f"Error finding slot: {e}")
            return None

    # Login
    if not login():
        logging.error(f"Court {court_index}: Could not login. Exiting.")
        driver.quit()
        return

    booking_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate?date={date}"
    driver.get(booking_url)
    time.sleep(2)

    attempts = 0
    max_attempts = 300
    while attempts < max_attempts:
        attempts += 1
        slot = find_slot()
        if slot:
            try:
                slot.click()
                logging.info(f"Court {court_index}: Slot clicked! Try booking manually as next step.")
                # Add your booking/payment automation here if needed
                break
            except Exception as e:
                logging.error(f"Click failed: {e}")
        else:
            if attempts % 10 == 0:
                logging.info(f"Court {court_index}: Attempt {attempts} - no slot yet.")
            driver.refresh()
            time.sleep(0.2)
    driver.quit()
    logging.info(f"Court {court_index}: Finished after {attempts} attempts.")

if __name__ == "__main__":
    # One process per court, default 4 courts
    procs = []
    for idx in range(1, 5):
        p = multiprocessing.Process(target=main, args=(idx,))
        p.start()
        procs.append(p)
    for p in procs:
        p.join()
