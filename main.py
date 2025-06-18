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

    async def quick_login(self):
        """Optimized login process"""
        try:
            logging.info("🔐 Fast login process...")

            # Navigate directly to login page
            await self.page.goto("https://clubspark.lta.org.uk/SouthwarkPark/Account/Login",
                                 wait_until='domcontentloaded')

            # Handle cookies immediately
            try:
                await self.page.click(".osano-cm-accept-all", timeout=1000)
            except:
                pass

            # Fill credentials in parallel
            await asyncio.gather(
                self.page.fill("input[placeholder='Username'], input[name='username']", username),
                self.page.fill("input[type='password']", password)
            )

            # Submit and wait for navigation
            await self.page.click("button[type='submit'], button:has-text('Log in')")

            # Wait for login success indicators
            try:
                await self.page.wait_for_selector("text=My bookings, text=Log out", timeout=5000)
                self.logged_in = True
                logging.info("✅ Login successful")
                return True
            except:
                logging.error("❌ Login failed")
                await self.screenshot("login_failed")
                return False

        except Exception as e:
            logging.error(f"Login error: {e}")
            return False

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
        booking_url = f"{https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=member"}
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
        await booker.cleanup()


# Run the booking
if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        logging.info("✅ Booking completed successfully!")
    else:
        logging.error("❌ Booking failed!")