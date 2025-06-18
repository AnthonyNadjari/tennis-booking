import os
import logging
import asyncio
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List
from playwright.async_api import async_playwright, Page, Browser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking.log'),
        logging.StreamHandler()
    ]
)


@dataclass
class BookingConfig:
    """Configuration for booking parameters"""
    account_number: str
    username: str
    password: str
    card_number: str
    card_expiry: str
    card_cvc: str
    date: str
    hour: int
    minutes: int

    @classmethod
    def from_env(cls) -> 'BookingConfig':
        """Create config from environment variables"""
        account_number = os.environ.get('ACCOUNT', '1')
        username = (os.environ.get('TENNIS_USERNAME2')
                    if account_number == '2'
                    else os.environ.get('TENNIS_USERNAME'))
        password = os.environ.get('TENNIS_PASSWORD')

        if not username or not password:
            raise ValueError("Username or password not defined!")

        return cls(
            account_number=account_number,
            username=username,
            password=password,
            card_number=os.environ.get('CARD_NUMBER', '5354562794845156'),
            card_expiry=os.environ.get('CARD_EXPIRY', '04/30'),
            card_cvc=os.environ.get('CARD_CVC', '666'),
            date=os.environ.get('BOOKING_DATE', '2025-06-16'),
            hour=int(os.environ.get('BOOKING_HOUR', '7')),
            minutes=int(os.environ.get('BOOKING_MINUTES', '0'))
        )

    @property
    def total_minutes(self) -> int:
        return (self.hour * 60) + self.minutes

    @property
    def time_str(self) -> str:
        return f"{self.hour:02d}:{self.minutes:02d}"


class TennisBookingBot:
    """Tennis court booking automation bot"""

    BASE_URL = "https://clubspark.lta.org.uk/SouthwarkPark"

    LOGIN_INDICATORS = ["My bookings", "Log out", "Sign out", "My account", "Account settings"]
    CONFIRMATION_WORDS = ["confirmed", "success", "booked", "reserved", "confirmation"]

    def __init__(self, config: BookingConfig):
        self.config = config
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        """Async context manager entry"""
        playwright = await async_playwright().__aenter__()
        self.browser = await playwright.chromium.launch(headless=True)
        context = await self.browser.new_context()
        self.page = await context.new_page()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.browser:
            await self.browser.close()

    async def take_screenshot(self, name: str) -> None:
        """Take screenshot with timestamp"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{name}_{timestamp}.png"
            await self.page.screenshot(path=filename)
            logging.info(f"📸 Screenshot saved: {filename}")
        except Exception as e:
            logging.error(f"Screenshot error: {e}")

    async def is_logged_in(self) -> bool:
        """Check if user is logged in"""
        try:
            content = await self.page.content()
            return any(indicator in content for indicator in self.LOGIN_INDICATORS)
        except:
            return False

    async def accept_cookies(self) -> None:
        """Accept cookies if present"""
        try:
            await self.page.click(".osano-cm-accept-all", timeout=2000)
            logging.info("✅ Cookies accepted")
        except:
            pass

    async def login(self) -> bool:
        """Perform login process"""
        if await self.is_logged_in():
            logging.info("✅ Already logged in!")
            return True

        logging.info("🔐 Starting login process...")

        try:
            await self.page.goto(self.BASE_URL)
            await self.page.wait_for_load_state('networkidle')
            await self.accept_cookies()

            await self.page.click("a:has-text('Sign in')", timeout=5000)
            await self.page.wait_for_timeout(1000)

            try:
                await self.page.click("button:has-text('Login')", timeout=2000)
            except:
                pass

            await self.page.fill("input[name='username']", self.config.username)
            await self.page.fill("input[name='password']", self.config.password)
            await self.page.click("button:has-text('Log in')")
            await self.page.wait_for_timeout(3000)

            if await self.is_logged_in():
                logging.info("✅ Login successful!")
                return True
            else:
                logging.error("❌ Login failed")
                await self.take_screenshot("login_failed")
                return False

        except Exception as e:
            logging.error(f"❌ Login error: {e}")
            await self.take_screenshot("login_error")
            return False

    async def find_available_slots(self) -> List[str]:
        """Find all available booking slots"""
        try:
            booking_links = await self.page.query_selector_all("a.book-interval.not-booked")
            available_slots = []

            for link in booking_links:
                data_test_id = await link.get_attribute('data-test-id') or ""
                if '|' in data_test_id:
                    parts = data_test_id.split('|')
                    if len(parts) >= 3:
                        time_minutes = int(parts[2])
                        hour = time_minutes // 60
                        minute = time_minutes % 60
                        available_slots.append(f"{hour:02d}:{minute:02d}")

            return available_slots
        except Exception as e:
            logging.error(f"Error finding slots: {e}")
            return []

    async def book_slot(self) -> bool:
        """Attempt to book the desired slot"""
        try:
            if not await self.is_logged_in():
                logging.warning("⚠️ Session lost, reconnecting...")
                if not await self.login():
                    return False

            await self.accept_cookies()
            target_time_minutes = self.config.total_minutes
            xpath_query = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{target_time_minutes}')]"

            try:
                await self.page.click(f"xpath={xpath_query}", timeout=1000)
                logging.info(f"🎯 Slot found directly at {self.config.time_str}!")
                return await self.complete_booking()
            except:
                booking_links = await self.page.query_selector_all("a.book-interval.not-booked")

                for link in booking_links:
                    data_test_id = await link.get_attribute('data-test-id') or ""
                    if '|' in data_test_id:
                        parts = data_test_id.split('|')
                        if len(parts) >= 3 and int(parts[2]) == target_time_minutes:
                            logging.info(f"🎯 Slot found at {self.config.time_str}!")
                            await link.click()
                            return await self.complete_booking()

            available_slots = await self.find_available_slots()
            logging.info(f"Available slots: {', '.join(available_slots) if available_slots else 'None'}")
            return False

        except Exception as e:
            logging.error(f"❌ Booking error: {e}")
            return False

    async def complete_booking(self) -> bool:
        """Complete the booking process after slot selection"""
        try:
            await self.page.wait_for_timeout(1000)

            if not await self.is_logged_in():
                logging.error("❌ Redirected to login after slot selection!")
                return False

            try:
                await self.page.click(".select2-selection--single")
                options = await self.page.query_selector_all(".select2-results__option")
                if len(options) >= 2:
                    await options[1].click()
            except Exception as e:
                logging.warning(f"Duration selection failed: {e}")

            await self.page.click("button:has-text('Continue')")
            await self.page.wait_for_timeout(1000)

            if not await self.is_logged_in():
                logging.error("❌ Redirected to login after Continue!")
                return False

            await self.page.click("#paynow")
            return await self.handle_payment()

        except Exception as e:
            logging.error(f"❌ Booking completion error: {e}")
            await self.take_screenshot("booking_error")
            return False

    async def handle_payment(self) -> bool:
        """Handle Stripe payment process"""
        try:
            logging.info("💳 Processing payment...")
            await self.page.wait_for_timeout(3000)

            if "login" in self.page.url.lower():
                logging.error("❌ Redirected to login instead of payment!")
                return False

            iframes = await self.page.query_selector_all("iframe[name^='__privateStripeFrame']")
            if len(iframes) < 3:
                logging.error("❌ Stripe iframes not found")
                await self.take_screenshot("stripe_error")
                return False

            await iframes[0].frame_locator("input[name='cardnumber']").fill(self.config.card_number)
            await iframes[1].frame_locator("input[name='exp-date']").fill(self.config.card_expiry)
            await iframes[2].frame_locator("input[name='cvc']").fill(self.config.card_cvc)

            await self.page.click("#cs-stripe-elements-submit-button")

            try:
                await self.page.wait_for_url("**/confirmation**", timeout=20000)
                logging.info("🎉 BOOKING CONFIRMED!")
                return True
            except:
                content = await self.page.content()
                if any(word in content.lower() for word in self.CONFIRMATION_WORDS):
                    logging.info("🎉 BOOKING LIKELY CONFIRMED!")
                    return True
                else:
                    logging.error("❌ Payment confirmation failed")
                    await self.take_screenshot("payment_failed")
                    return False

        except Exception as e:
            logging.error(f"❌ Payment error: {e}")
            await self.take_screenshot("payment_error")
            return False

    async def run_booking_loop(self, max_attempts: int = 300, max_duration: int = 300) -> bool:
        """Main booking loop with retry logic"""
        if not await self.login():
            logging.error("❌ Initial login failed!")
            return False

        booking_url = f"{self.BASE_URL}/Booking/BookByDate#?date={self.config.date}&role=member"
        await self.page.goto(booking_url)
        await self.page.wait_for_load_state('networkidle')

        start_time = datetime.now()
        attempt = 0

        logging.info(f"🎾 Starting booking attempts for {self.config.date} at {self.config.time_str}")
        logging.info(f"👤 Account: {self.config.account_number}")

        while attempt < max_attempts and (datetime.now() - start_time).seconds < max_duration:
            attempt += 1

            if attempt % 20 == 0 and not await self.is_logged_in():
                logging.warning("⚠️ Session expired, reconnecting...")
                if not await self.login():
                    logging.error("❌ Reconnection failed!")
                    break
                await self.page.goto(booking_url)
                await self.page.wait_for_load_state('networkidle')

            if attempt % 10 == 0:
                elapsed = (datetime.now() - start_time).seconds
                logging.info(f"🔄 Attempt {attempt}/{max_attempts} (elapsed: {elapsed}s)")

            if await self.book_slot():
                logging.info("🎉 BOOKING SUCCESSFUL!")
                return True

            await self.page.reload()
            await self.page.wait_for_timeout(500)

        elapsed = (datetime.now() - start_time).seconds
        logging.info(f"✅ Script finished after {elapsed}s and {attempt} attempts")
        return False


async def main():
    """Main execution function"""
    try:
        config = BookingConfig.from_env()

        async with TennisBookingBot(config) as bot:
            success = await bot.run_booking_loop()
            if success:
                logging.info("🎉 Booking completed successfully!")
            else:
                logging.info("❌ Booking attempts completed without success")

    except ValueError as e:
        logging.error(f"❌ Configuration error: {e}")
    except Exception as e:
        logging.error(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())