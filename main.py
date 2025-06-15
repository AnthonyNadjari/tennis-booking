from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import os


# Configure Chrome options for cloud deployment
def get_chrome_options():
    options = Options()
    options.add_argument("--headless")  # Run in background
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--window-size=1920,1080")
    return options


# Input variables for login credentials
username = "anthonadj92"  # anthonadj92 or anthonadj
password = "SorLouise2!"  # SorLouise2!

# Set the date and hour for booking
date = "2025-06-15"
hour = 7

# Format hour and next_hour with leading zeros
hour_str = f"{hour:02d}:00"
next_hour = f"{(hour + 1) % 24:02d}:00"

# Convert hour to total minutes as a string
hour_str_minutes = str(hour * 60)


# Initialize the Chrome driver with cloud-compatible settings
def init_driver():
    try:
        options = get_chrome_options()
        # Try to use system ChromeDriver (Railway should have it)
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"❌ Failed to initialize Chrome driver: {e}")
        print("Make sure Chrome and ChromeDriver are installed")
        raise


driver = init_driver()


def login_first(username, password):
    try:
        if "Sign in" not in driver.page_source:
            print("✅ Already logged in!")
            return True

        print("🔐 Step 1: Clicking Sign in...")
        sign_in_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in')]")))
        sign_in_btn.click()

        print("🔐 Step 2: Clicking Login button...")
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login')]")))
        login_button.click()

        print("📝 Step 3: Entering credentials...")
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Username']")))
        username_field.clear()
        username_field.send_keys(username)

        password_field = driver.find_element(By.XPATH, "//input[@placeholder='Password']")
        password_field.clear()
        password_field.send_keys(password)

        final_login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
        final_login_btn.click()

        print("✅ Login submitted!")
        WebDriverWait(driver, 10).until(lambda d: "BookByDate" in d.title)
        return True

    except Exception as e:
        print(f"❌ Login failed: {e}")
        return False


def try_booking():
    try:
        try:
            accept_all_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "osano-cm-accept-all")))
            accept_all_btn.click()
        except Exception as e:
            print(f"No cookie banner or already accepted: {e}")

        am_slots = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, f'div[data-system-start-time="{hour_str_minutes}"]'))
        )
        print(f"Found {len(am_slots)} {hour_str} time slots")

        for slot in am_slots:
            try:
                booking_link = slot.find_element(By.CSS_SELECTOR, 'a.book-interval.not-booked')
                cost_span = booking_link.find_element(By.CLASS_NAME, "cost")

                if "£3.60" in cost_span.text or "£4.95" in cost_span.text:
                    print(f"✅ Found {hour_str} slot: {booking_link.text}")
                    booking_link.click()

                    try:
                        select2_selection = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, ".select2-selection")))
                        select2_selection.click()

                        options = WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".select2-results__option")))
                        if len(options) >= 2:
                            options[1].click()
                        else:
                            option_next_hour = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, f"//li[contains(text(), '{next_hour}')]")))
                            option_next_hour.click()
                        print("✅ Selected next hour option")

                        continue_btn = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
                        continue_btn.click()
                        print("✅ Clicked Continue button")

                        paynow_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "paynow")))
                        paynow_btn.click()
                        print("✅ Clicked Confirm and pay button")

                        print("💳 Fast Stripe payment...")

                        # Wait for all iframes to be available
                        iframes = WebDriverWait(driver, 15).until(
                            EC.presence_of_all_elements_located(
                                (By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
                        )

                        # Enter card number
                        driver.switch_to.frame(iframes[0])
                        card_field = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cardnumber']"))
                        )
                        card_field.send_keys("5354562794845156")
                        driver.switch_to.default_content()
                        print("✅ Card number entered")

                        # Enter expiry date
                        driver.switch_to.frame(iframes[1])
                        expiry_field = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='exp-date']"))
                        )
                        expiry_field.send_keys("04/30")
                        driver.switch_to.default_content()
                        print("✅ Expiry date entered")

                        # Enter CVC
                        driver.switch_to.frame(iframes[2])
                        cvc_field = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cvc']"))
                        )
                        cvc_field.send_keys("666")
                        driver.switch_to.default_content()
                        print("✅ CVC entered")

                        # Click the pay button
                        pay_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
                        )
                        pay_button.click()
                        print("✅ Payment submitted!")

                        WebDriverWait(driver, 20).until(EC.url_contains("confirmation"))
                        print("🎉 BOOKING COMPLETED!")
                        return True

                    except Exception as e:
                        print(f"Select2 dropdown failed: {e}")
                        try:
                            hidden_select = driver.find_element(By.ID, "booking-duration")
                            Select(hidden_select).select_by_index(1)
                            driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]").click()
                            print("✅ Used hidden select fallback")
                            return True
                        except Exception as e2:
                            print(f"Hidden select fallback failed: {e2}")
                            return False

            except Exception as e:
                print(f"Slot not bookable: {e}")
                continue

    except Exception as e:
        print(f"No {hour_str} slots found: {e}")

    return False


# Main execution
try:
    print("🚀 Starting tennis court booking bot...")

    # Navigate to the booking page
    driver.get(f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=guest")

    # Attempt to log in
    if login_first(username, password):
        print("✅ Login successful, attempting booking...")

        # Try booking (limited attempts for cloud environment)
        max_attempts = 5
        for attempt in range(max_attempts):
            print(f"🔄 Booking attempt {attempt + 1}/{max_attempts}")
            if try_booking():
                print("✅ Booking attempt completed!")
                break
            else:
                if attempt < max_attempts - 1:
                    print("No available slots found. Refreshing...")
                    time.sleep(2)
                    driver.refresh()
                else:
                    print("❌ No slots found after all attempts")
    else:
        print("❌ Login failed, cannot proceed with booking")

except Exception as e:
    print(f"❌ Script error: {e}")

finally:
    # Always close the driver
    try:
        driver.quit()
        print("🔒 Browser closed")
    except:
        pass