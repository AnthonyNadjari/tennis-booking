from playwright.async_api import async_playwright
import asyncio
import os
import logging
from datetime import datetime
import time

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking.log'),
        logging.StreamHandler()
    ]
)


import subprocess
import sys
import os


def ensure_playwright_setup():
    """Ensure Playwright is properly set up"""
    try:
        # Check if already installed
        chromium_path = "/home/runner/.cache/ms-playwright/chromium-1091/chrome-linux/chrome"
        if os.path.exists(chromium_path):
            print("✅ Playwright Chromium already installed")
            return True

        print("🔧 Installing Playwright Chromium...")
        result = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"],
                                capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Playwright Chromium installed successfully")
            return True
        else:
            print(f"❌ Installation failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Setup error: {e}")
        return False




# Environment variables
account_number = os.environ.get('ACCOUNT', '1')
username = os.environ.get('TENNIS_USERNAME2' if account_number == '2' else 'TENNIS_USERNAME')
password = os.environ.get('TENNIS_PASSWORD')
card_number = os.environ.get('CARD_NUMBER', '5354562794845156')
card_expiry = os.environ.get('CARD_EXPIRY', '04/30')
card_cvc = os.environ.get('CARD_CVC', '666')
date = os.environ.get('BOOKING_DATE', '2025-06-16')
hour = int(os.environ.get('BOOKING_HOUR', '7'))
minutes = int(os.environ.get('BOOKING_MINUTES', '0'))

# Calculate target time
target_time_minutes = hour * 60 + minutes
hour_str = f"{hour:02d}:{minutes:02d}"

logging.info(f"🎾 Booking for {date} at {hour_str} (Account: {account_number})")


class FastCourtBooker:
    def __init__(self):
        self.page = None
        self.context = None
        self.browser = None
        self.logged_in = False

    async def init_browser(self):
        """Initialize Playwright browser with optimal settings"""
        playwright = await async_playwright().start()

        # Optimized browser settings
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )

        # Create context with session persistence
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )

        # Enable request interception for faster loading
        await self.context.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}",
                           lambda route: route.abort())

        self.page = await self.context.new_page()

        # Set faster timeouts
        self.page.set_default_timeout(5000)
        self.page.set_default_navigation_timeout(10000)

    async def screenshot(self, name):
        """Take screenshot for debugging"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await self.page.screenshot(path=f"screenshot_{name}_{timestamp}.png")
            logging.info(f"📸 Screenshot: {name}")
        except Exception as e:
            logging.error(f"Screenshot error: {e}")

async def login_first(self):
    """Direct conversion of your working Selenium login"""
    try:
        logging.info("🔐 Processus de connexion complet...")
        
        # Navigate to main page first
        await self.page.goto("https://clubspark.lta.org.uk/SouthwarkPark", wait_until='domcontentloaded')
        await asyncio.sleep(2)
        
        # Accept cookies if present
        try:
            await self.page.click(".osano-cm-accept-all", timeout=500)
            await asyncio.sleep(0.5)
        except:
            pass

        # Step 1: Click Sign in
        try:
            await self.page.click("//a[contains(text(), 'Sign in') or contains(@href, 'login')]", timeout=10000)
            logging.info("✅ Cliqué sur Sign in")
            await asyncio.sleep(2)
        except Exception as e:
            logging.warning(f"Sign in non trouvé: {e}")
            # Try direct navigation to login
            await self.page.goto("https://clubspark.lta.org.uk/SouthwarkPark/Account/Login")
            await asyncio.sleep(2)

        # Step 2: Click Login button if needed
        try:
            await self.page.click("//button[contains(text(), 'Login') or contains(text(), 'Log in')]", timeout=5000)
            logging.info("✅ Cliqué sur Login")
            await asyncio.sleep(2)
        except:
            pass

        # Step 3: Fill credentials
        try:
            # Wait for form to be present
            await self.page.wait_for_selector("//input[@placeholder='Username' or @name='username' or @id='username']", timeout=10000)
            
            await self.page.fill("//input[@placeholder='Username' or @name='username' or @id='username']", username)
            logging.info("✅ Username saisi")

            await self.page.fill("//input[@placeholder='Password' or @name='password' or @id='password' or @type='password']", password)
            logging.info("✅ Password saisi")

            # Submit login
            await self.page.click("//button[contains(text(), 'Log in') or contains(text(), 'Login') or @type='submit']")
            logging.info("✅ Login soumis")

            # Wait for login to complete
            await asyncio.sleep(3)
            
            # Verify login succeeded
            if await self.check_login_status():
                logging.info("✅ Login confirmé!")
                return True
            else:
                logging.error("❌ Login non confirmé")
                await self.screenshot("login_failed")
                return False

        except Exception as e:
            logging.error(f"Erreur saisie credentials: {e}")
            await self.screenshot("login_error")
            return False

    except Exception as e:
        logging.error(f"❌ Erreur login: {e}")
        await self.screenshot("login_error")
        return False

async def check_login_status(self):
    """Convert your working login check"""
    try:
        page_content = await self.page.content()
        # Multiple indicators of being logged in
        logged_in_indicators = ["My bookings", "Log out", "Sign out", "My account", "Account settings"]
        
        for indicator in logged_in_indicators:
            if indicator in page_content:
                return True
        
        # Check for login form as negative indicator
        current_url = self.page.url
        if "username" in page_content.lower() and "password" in page_content.lower():
            if "login" in current_url.lower() or "signin" in current_url.lower():
                return False
        
        return False
    except:
        return False

async def ensure_logged_in(self):
    """Convert your ensure_logged_in logic"""
    if await self.check_login_status():
        logging.info("✅ Déjà connecté!")
        return True
    
    logging.info("🔐 Pas connecté, tentative de connexion...")
    return await self.login_first()

    async def check_login_status(self):
        """Quick login status check"""
        try:
            # Check for logout button or account menu
            logout_btn = await self.page.query_selector("text=Log out, text=Sign out, text=My account")
            return logout_btn is not None
        except:
            return False

    async def find_slot_fast(self):
        """Ultra-fast slot detection"""
        try:
            # Direct XPath for target slot
            slot_selector = f"a.book-interval.not-booked[data-test-id*='|{target_time_minutes}']"

            # Wait for booking grid to load
            await self.page.wait_for_selector("a.book-interval", timeout=3000)

            # Try direct selection first
            slot = await self.page.query_selector(slot_selector)
            if slot:
                logging.info(f"🎯 SLOT FOUND at {hour_str}!")
                await slot.click()
                return True

            # Fallback: check all slots
            slots = await self.page.query_selector_all("a.book-interval.not-booked")
            for slot in slots:
                data_test_id = await slot.get_attribute('data-test-id')
                if data_test_id and f"|{target_time_minutes}" in data_test_id:
                    logging.info(f"🎯 SLOT FOUND (fallback) at {hour_str}!")
                    await slot.click()
                    return True

            return False

        except Exception as e:
            logging.error(f"Slot detection error: {e}")
            return False

    async def complete_booking_fast(self):
        """Optimized booking completion"""
        try:
            # Quick duration selection
            try:
                await self.page.click(".select2-selection")
                await self.page.click(".select2-results__option:nth-child(2)", timeout=2000)
            except:
                try:
                    await self.page.select_option("#booking-duration", index=1)
                except:
                    pass

            # Continue to payment
            await self.page.click("button:has-text('Continue')")

            # Wait for payment form
            await self.page.wait_for_selector("#paynow", timeout=10000)
            await self.page.click("#paynow")

            return await self.handle_stripe_fast()

        except Exception as e:
            logging.error(f"Booking completion error: {e}")
            await self.screenshot("booking_error")
            return False

    async def handle_stripe_fast(self):
        """Optimized Stripe payment"""
        try:
            logging.info("💳 Processing Stripe payment...")

            # Wait for all Stripe iframes
            await self.page.wait_for_selector("iframe[name^='__privateStripeFrame']", timeout=15000)

            # Get all iframes
            iframes = await self.page.query_selector_all("iframe[name^='__privateStripeFrame']")

            if len(iframes) < 3:
                logging.error("❌ Insufficient Stripe iframes")
                return False

            # Fill payment details in parallel
            await asyncio.gather(
                self.fill_stripe_field(iframes[0], "input[name='cardnumber']", card_number),
                self.fill_stripe_field(iframes[1], "input[name='exp-date']", card_expiry),
                self.fill_stripe_field(iframes[2], "input[name='cvc']", card_cvc)
            )

            # Submit payment
            await self.page.click("#cs-stripe-elements-submit-button")
            logging.info("✅ Payment submitted")

            # Wait for confirmation
            try:
                await self.page.wait_for_url("**/confirmation**", timeout=30000)
                logging.info("🎉 BOOKING CONFIRMED!")
                await self.screenshot("success")
                return True
            except:
                # Check for success indicators in page content
                await self.page.wait_for_timeout(3000)
                content = await self.page.content()
                if any(word in content.lower() for word in ["confirmed", "success", "booked"]):
                    logging.info("🎉 BOOKING LIKELY CONFIRMED!")
                    return True
                return False

        except Exception as e:
            logging.error(f"Stripe payment error: {e}")
            await self.screenshot("payment_error")
            return False

    async def fill_stripe_field(self, iframe, selector, value):
        """Fill individual Stripe field"""
        frame = await iframe.content_frame()
        await frame.fill(selector, value)

    async def cleanup(self):
        """Clean up resources"""
        if self.browser:
            await self.browser.close()


async def main():
    """Main booking execution"""
    booker = FastCourtBooker()
    start_time = time.time()

    try:
        # Initialize browser
        await booker.init_browser()

        # Login
        if not await booker.quick_login():
            logging.error("❌ Login failed!")
            return False

        # Navigate to booking page
        booking_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=member"
        await booker.page.goto(booking_url, wait_until='domcontentloaded')

        # Booking loop
        attempt = 0
        max_attempts = 200

        while attempt < max_attempts:
            attempt += 1
            elapsed = int(time.time() - start_time)

            logging.info(f"🔄 Attempt {attempt} (time: {elapsed}s)")

            # Check login every 20 attempts
            if attempt % 20 == 0:
                if not await booker.check_login_status():
                    logging.warning("⚠️ Session lost, re-login...")
                    if not await booker.quick_login():
                        break
                    await booker.page.goto(booking_url, wait_until='domcontentloaded')

            # Try to find and book slot
            if await booker.find_slot_fast():
                if await booker.complete_booking_fast():
                    total_time = int(time.time() - start_time)
                    logging.info(f"🎉 SUCCESS in {total_time}s after {attempt} attempts!")
                    return True
                else:
                    # Booking failed, refresh and try again
                    await booker.page.reload(wait_until='domcontentloaded')
            else:
                # No slot found, quick refresh
                await booker.page.reload(wait_until='domcontentloaded')
                await asyncio.sleep(0.2)  # Minimal delay

        logging.info("❌ Max attempts reached")
        return False

    except Exception as e:
        logging.error(f"❌ Critical error: {e}")
        return False
    finally:
        try:
            if booker.context:
                await booker.context.close()
            if booker.browser:
                await booker.browser.close()
        except:
            pass



# Run the booking
if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        logging.info("✅ Booking completed successfully!")
    else:
        logging.error("❌ Booking failed!")
