import os
import logging
import asyncio
import subprocess
import sys
from datetime import datetime
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking.log'),
        logging.StreamHandler()
    ]
)

# Configuration from environment variables
ACCOUNT = os.environ.get('ACCOUNT', '1')
USERNAME = os.environ.get('TENNIS_USERNAME2') if ACCOUNT == '2' else os.environ.get('TENNIS_USERNAME')
PASSWORD = os.environ.get('TENNIS_PASSWORD')
CARD_NUMBER = os.environ.get('CARD_NUMBER', '5354562794845156')
CARD_EXPIRY = os.environ.get('CARD_EXPIRY', '04/30')
CARD_CVC = os.environ.get('CARD_CVC', '666')
BOOKING_DATE = os.environ.get('BOOKING_DATE', '2025-06-16')
BOOKING_HOUR = int(os.environ.get('BOOKING_HOUR', '7'))
BOOKING_MINUTES = int(os.environ.get('BOOKING_MINUTES', '0'))

if not USERNAME or not PASSWORD:
    logging.error("❌ Username or password not defined!")
    exit(1)

# Constants
BASE_URL = "https://clubspark.lta.org.uk/SouthwarkPark"
LOGIN_INDICATORS = ["My bookings", "Log out", "Sign out", "My account"]
CONFIRMATION_WORDS = ["confirmed", "success", "booked", "reserved", "confirmation"]
TARGET_TIME_MINUTES = (BOOKING_HOUR * 60) + BOOKING_MINUTES
TIME_STR = f"{BOOKING_HOUR:02d}:{BOOKING_MINUTES:02d}"

logging.info(f"🎾 Booking for {BOOKING_DATE} at {TIME_STR}")
logging.info(f"👤 Account: {ACCOUNT}")



###################### 2





async def install_browsers():
    """Install Playwright browsers if needed"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            await browser.close()
        logging.info("✅ Browsers already installed")
    except Exception:
        logging.info("📦 Installing browsers...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        logging.info("✅ Browsers installed")

async def take_screenshot(page, name):
    """Take screenshot with timestamp"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{name}_{timestamp}.png"
        await page.screenshot(path=filename)
        logging.info(f"📸 Screenshot: {filename}")
    except Exception as e:
        logging.error(f"Screenshot error: {e}")

async def is_logged_in(page):
    """Check if logged in"""
    try:
        content = await page.content()
        return any(indicator in content for indicator in LOGIN_INDICATORS)
    except:
        return False

async def accept_cookies(page):
    """Accept cookies if present"""
    try:
        await page.click(".osano-cm-accept-all", timeout=2000)
        logging.info("✅ Cookies accepted")
    except:
        pass


async def debug_page_content(page, step_name):
    """Debug function to see page content"""
    try:
        content = await page.content()
        with open(f"debug_{step_name}.html", "w", encoding="utf-8") as f:
            f.write(content)
        logging.info(f"📄 Page content saved to debug_{step_name}.html")

        # Also log the current URL
        current_url = page.url
        logging.info(f"🔗 Current URL: {current_url}")

    except Exception as e:
        logging.error(f"Debug error: {e}")


################# 3

async def login(page):
    """Login to the website with improved error handling and debugging"""
    if await is_logged_in(page):
        logging.info("✅ Already logged in")
        return True

    logging.info("🔐 Starting login process...")

    try:
        # Navigate to main page
        await page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(2000)
        await accept_cookies(page)

        # DEBUG: Save page content after navigation
        await debug_page_content(page, "after_navigation")
        await take_screenshot(page, "before_login")

        # Look for sign in link
        sign_in_selectors = [
            "a:has-text('Sign in')",
            "a[href*='login']",
            "a[href*='Login']",
            ".login-link",
            "#login-link"
        ]

        clicked_sign_in = False
        for selector in sign_in_selectors:
            try:
                await page.click(selector, timeout=3000)
                logging.info(f"✅ Clicked sign in with selector: {selector}")
                clicked_sign_in = True
                break
            except:
                continue

        if not clicked_sign_in:
            logging.error("❌ Could not find sign in link")
            # DEBUG: Save page content when sign in link not found
            await debug_page_content(page, "no_signin_link")
            await take_screenshot(page, "no_signin_link")
            return False

        await page.wait_for_timeout(3000)

        # DEBUG: Save page content after clicking sign in
        await debug_page_content(page, "after_signin_click")

        # Try to click Login button if it exists
        login_button_selectors = [
            "button:has-text('Login')",
            "input[type='submit'][value*='Login']",
            ".login-button",
            "#login-button"
        ]

        for selector in login_button_selectors:
            try:
                await page.click(selector, timeout=2000)
                logging.info(f"✅ Clicked login button with selector: {selector}")
                break
            except:
                continue

        await page.wait_for_timeout(2000)

        # DEBUG: Save page content before filling credentials
        await debug_page_content(page, "before_credentials")

        # Fill username
        username_selectors = [
            "input[name='username']",
            "input[name='email']",
            "input[type='email']",
            "input[id*='username']",
            "input[id*='email']"
        ]

        filled_username = False
        for selector in username_selectors:
            try:
                await page.fill(selector, USERNAME)
                logging.info(f"✅ Filled username with selector: {selector}")
                filled_username = True
                break
            except:
                continue

        if not filled_username:
            logging.error("❌ Could not find username field")
            # DEBUG: Save page content when username field not found
            await debug_page_content(page, "no_username_field")
            await take_screenshot(page, "no_username_field")
            return False

        # Fill password
        password_selectors = [
            "input[name='password']",
            "input[type='password']",
            "input[id*='password']"
        ]

        filled_password = False
        for selector in password_selectors:
            try:
                await page.fill(selector, PASSWORD)
                logging.info(f"✅ Filled password with selector: {selector}")
                filled_password = True
                break
            except:
                continue

        if not filled_password:
            logging.error("❌ Could not find password field")
            # DEBUG: Save page content when password field not found
            await debug_page_content(page, "no_password_field")
            await take_screenshot(page, "no_password_field")
            return False

        # DEBUG: Save page content after filling credentials
        await debug_page_content(page, "after_credentials")

        # Submit login
        submit_selectors = [
            "button:has-text('Log in')",
            "button:has-text('Login')",
            "button:has-text('Sign in')",
            "input[type='submit']",
            "button[type='submit']",
            ".login-submit",
            "#login-submit"
        ]

        submitted = False
        for selector in submit_selectors:
            try:
                await page.click(selector, timeout=3000)
                logging.info(f"✅ Submitted login with selector: {selector}")
                submitted = True
                break
            except:
                continue

        if not submitted:
            try:
                await page.press("input[name='password']", "Enter")
                logging.info("✅ Submitted login with Enter key")
                submitted = True
            except:
                pass

        if not submitted:
            logging.error("❌ Could not submit login form")
            # DEBUG: Save page content when submit fails
            await debug_page_content(page, "no_submit_button")
            await take_screenshot(page, "no_submit_button")
            return False

        # Wait for login to complete
        await page.wait_for_timeout(8000)

        # DEBUG: Save page content after login attempt
        await debug_page_content(page, "after_login_attempt")

        # Check if login was successful
        if await is_logged_in(page):
            logging.info("✅ Login successful!")
            await take_screenshot(page, "login_success")
            return True
        else:
            logging.error("❌ Login failed")
            await take_screenshot(page, "login_failed")
            return False

    except Exception as e:
        logging.error(f"❌ Login error: {e}")
        await take_screenshot(page, "login_exception")
        return False



async def find_available_slots(page):
    """Find all available slots"""
    try:
        await page.wait_for_selector("a.book-interval", timeout=5000)
        links = await page.query_selector_all("a.book-interval.not-booked")
        slots = []

        for link in links:
            data_id = await link.get_attribute('data-test-id') or ""
            if '|' in data_id:
                parts = data_id.split('|')
                if len(parts) >= 3:
                    try:
                        minutes = int(parts[2])
                        hour = minutes // 60
                        minute = minutes % 60
                        slots.append(f"{hour:02d}:{minute:02d}")
                    except:
                        continue

        return sorted(list(set(slots)))
    except Exception as e:
        logging.error(f"Error finding slots: {e}")
        return []


async def book_slot(page):
    """Try to book the desired slot"""
    try:
        if not await is_logged_in(page):
            logging.warning("⚠️ Session lost, reconnecting...")
            if not await login(page):
                return False

        await accept_cookies(page)
        await page.wait_for_selector("a.book-interval", timeout=10000)

        # Try direct booking
        xpath = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{TARGET_TIME_MINUTES}')]"
        try:
            await page.click(f"xpath={xpath}", timeout=2000)
            logging.info(f"🎯 Slot found at {TIME_STR}!")
            return await complete_booking(page)
        except:
            # Try manual search
            links = await page.query_selector_all("a.book-interval.not-booked")
            for link in links:
                try:
                    data_id = await link.get_attribute('data-test-id') or ""
                    if '|' in data_id:
                        parts = data_id.split('|')
                        if len(parts) >= 3 and int(parts[2]) == TARGET_TIME_MINUTES:
                            logging.info(f"🎯 Slot found at {TIME_STR}!")
                            await link.click()
                            return await complete_booking(page)
                except:
                    continue

        # Show available slots
        available = await find_available_slots(page)
        if available:
            logging.info(f"Available: {', '.join(available[:10])}")
        else:
            logging.info("No slots available")
        return False

    except Exception as e:
        logging.error(f"❌ Booking error: {e}")
        await take_screenshot(page, "booking_error")
        return False




 ################ 5
async def complete_booking(page):
    """Complete the booking process"""
    try:
        await page.wait_for_timeout(2000)

        if not await is_logged_in(page):
            logging.error("❌ Redirected to login!")
            return False

        # Select duration
        try:
            await page.click(".select2-selection--single", timeout=5000)
            await page.wait_for_timeout(1000)
            options = await page.query_selector_all(".select2-results__option")
            if len(options) >= 2:
                await options[1].click()
                logging.info("✅ Duration selected")
        except Exception as e:
            logging.warning(f"Duration selection failed: {e}")

        # Continue to payment
        await page.click("button:has-text('Continue')", timeout=10000)
        await page.wait_for_timeout(3000)

        if not await is_logged_in(page):
            logging.error("❌ Redirected to login after Continue!")
            return False

        # Start payment
        await page.click("#paynow", timeout=10000)
        return await handle_payment(page)

    except Exception as e:
        logging.error(f"❌ Booking completion error: {e}")
        await take_screenshot(page, "booking_error")
        return False


async def handle_payment(page):
    """Handle Stripe payment"""
    try:
        logging.info("💳 Processing payment...")
        await page.wait_for_timeout(5000)

        if "login" in page.url.lower():
            logging.error("❌ Redirected to login instead of payment!")
            return False

        # Wait for Stripe iframes
        for retry in range(3):
            iframes = await page.query_selector_all("iframe[name^='__privateStripeFrame']")
            if len(iframes) >= 3:
                break
            await page.wait_for_timeout(2000)

        if len(iframes) < 3:
            logging.error("❌ Stripe iframes not found")
            await take_screenshot(page, "stripe_error")
            return False

        # Fill payment details
        await iframes[0].frame_locator("input[name='cardnumber']").fill(CARD_NUMBER)
        await iframes[1].frame_locator("input[name='exp-date']").fill(CARD_EXPIRY)
        await iframes[2].frame_locator("input[name='cvc']").fill(CARD_CVC)

        # Submit payment
        await page.click("#cs-stripe-elements-submit-button")

        # Wait for confirmation
        try:
            await page.wait_for_url("**/confirmation**", timeout=20000)
            logging.info("🎉 BOOKING CONFIRMED!")
            return True
        except:
            content = await page.content()
            if any(word in content.lower() for word in CONFIRMATION_WORDS):
                logging.info("🎉 BOOKING LIKELY CONFIRMED!")
                return True
            else:
                logging.error("❌ Payment confirmation failed")
                await take_screenshot(page, "payment_failed")
                return False

    except Exception as e:
        logging.error(f"❌ Payment error: {e}")
        await take_screenshot(page, "payment_error")
        return False

######### 6

async def main():
    """Main execution function"""
    try:
        # Install browsers
        await install_browsers()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()

            # Login first
            if not await login(page):
                logging.error("❌ Initial login failed!")
                return

            # Navigate to booking page
            booking_url = f"{BASE_URL}/Booking/BookByDate#?date={BOOKING_DATE}&role=member"
            await page.goto(booking_url, wait_until='networkidle')

            start_time = datetime.now()
            attempt = 0
            max_attempts = 300
            max_duration = 300

            logging.info(f"🎾 Starting booking attempts...")

            while attempt < max_attempts and (datetime.now() - start_time).seconds < max_duration:
                attempt += 1

                # Periodic login check
                if attempt % 20 == 0 and not await is_logged_in(page):
                    logging.warning("⚠️ Session expired, reconnecting...")
                    if not await login(page):
                        logging.error("❌ Reconnection failed!")
                        break
                    await page.goto(booking_url, wait_until='networkidle')

                if attempt % 10 == 0:
                    elapsed = (datetime.now() - start_time).seconds
                    logging.info(f"🔄 Attempt {attempt}/{max_attempts} (elapsed: {elapsed}s)")

                if await book_slot(page):
                    logging.info("🎉 BOOKING SUCCESSFUL!")
                    break

                await page.reload()
                await page.wait_for_timeout(500)

            elapsed = (datetime.now() - start_time).seconds
            logging.info(f"✅ Script finished after {elapsed}s and {attempt} attempts")

            await browser.close()

    except Exception as e:
        logging.error(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
