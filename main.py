from playwright.async_api import async_playwright
import asyncio
import os
import logging
from datetime import datetime
import time

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('booking.log'), logging.StreamHandler()])

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

if not username or not password:
    logging.error("❌ Username ou password non définis!")
    exit(1)

target_time_minutes = hour * 60 + minutes
hour_str = f"{hour:02d}:{minutes:02d}"
logging.info(f"🎾 Booking {date} at {hour_str} (Account: {account_number})")


class FastCourtBooker:
    def __init__(self):
        self.page = None
        self.context = None
        self.browser = None

    async def init_browser(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self.page = await self.context.new_page()
        logging.info("✅ Browser initialized")

    async def screenshot(self, name):
        try:
            await self.page.screenshot(path=f"screenshot_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        except:
            pass

    async def check_login_status(self):
        try:
            content = await self.page.content()
            return any(indicator in content for indicator in ["My bookings", "Log out", "Sign out", "My account"])
        except:
            return False

    async def login_first(self):
        try:
            logging.info("🔐 Login process...")
            await self.page.goto("https://clubspark.lta.org.uk/SouthwarkPark")
            await asyncio.sleep(2)

            try:
                await self.page.click(".osano-cm-accept-all", timeout=500)
            except:
                pass

            try:
                await self.page.click("//a[contains(text(), 'Sign in') or contains(@href, 'login')]", timeout=10000)
                await asyncio.sleep(2)
            except:
                await self.page.goto("https://clubspark.lta.org.uk/SouthwarkPark/Account/Login")
                await asyncio.sleep(2)

            try:
                await self.page.click("//button[contains(text(), 'Login') or contains(text(), 'Log in')]", timeout=5000)
            except:
                pass

            await self.page.wait_for_selector("//input[@placeholder='Username' or @name='username' or @id='username']",
                                              timeout=10000)
            await self.page.fill("//input[@placeholder='Username' or @name='username' or @id='username']", username)
            await self.page.fill("//input[@type='password']", password)
            await self.page.click("//button[contains(text(), 'Log in') or @type='submit']")
            await asyncio.sleep(3)

            if await self.check_login_status():
                logging.info("✅ Login successful")
                return True
            else:
                await self.screenshot("login_failed")
                return False
        except Exception as e:
            logging.error(f"❌ Login error: {e}")
            return False

    async def find_and_book_slot(self):
        try:
            if not await self.check_login_status():
                return False

            await self.page.wait_for_selector("a.book-interval", timeout=5000)
            xpath_query = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{target_time_minutes}')]"

            try:
                await self.page.click(xpath_query, timeout=2000)
                logging.info(f"🎯 SLOT FOUND at {hour_str}!")
                await asyncio.sleep(1.5)
                return await self.complete_booking()
            except:
                booking_links = await self.page.query_selector_all("a.book-interval.not-booked")
                for link in booking_links:
                    data_test_id = await link.get_attribute('data-test-id') or ""
                    if f"|{target_time_minutes}" in data_test_id:
                        await link.click()
                        await asyncio.sleep(1.5)
                        return await self.complete_booking()
            return False
        except Exception as e:
            logging.error(f"❌ Slot error: {e}")
            return False

    async def complete_booking(self):
        try:
            # Select duration
            try:
                await self.page.click(".select2-selection")
                await asyncio.sleep(0.3)
                options = await self.page.query_selector_all(".select2-results__option")
                if len(options) >= 2: await options[1].click()
            except:
                try:
                    await self.page.select_option("#booking-duration", index=1)
                except:
                    pass

            # Continue
            await self.page.click("//button[contains(text(), 'Continue')]")
            await asyncio.sleep(2)

            # Payment
            await self.page.wait_for_selector("#paynow", timeout=10000)
            await self.page.click("#paynow")
            await asyncio.sleep(2)

            return await self.handle_stripe()
        except Exception as e:
            logging.error(f"❌ Booking error: {e}")
            return False

    async def handle_stripe(self):
        try:
            logging.info("💳 Processing payment...")
            iframes = await self.page.query_selector_all("iframe[name^='__privateStripeFrame']")

            if len(iframes) < 3:
                return False

            # Fill card details
            for i, (iframe, value) in enumerate(zip(iframes[:3], [card_number, card_expiry, card_cvc])):
                frame = await iframe.content_frame()
                selectors = [
                    ["input[name='cardnumber']", "input[placeholder*='card']"],
                    ["input[name='exp-date']", "input[placeholder*='MM']"],
                    ["input[name='cvc']", "input[placeholder*='CVC']"]
                ]
                for selector in selectors[i]:
                    try:
                        await frame.fill(selector, value)
                        break
                    except:
                        continue

            # Submit payment
            await self.page.click("#cs-stripe-elements-submit-button")

            # Wait for confirmation
            try:
                await self.page.wait_for_url("**/confirmation**", timeout=30000)
                logging.info("🎉 BOOKING CONFIRMED!")
                return True
            except:
                await asyncio.sleep(5)
                content = await self.page.content()
                if any(word in content.lower() for word in ["confirmed", "success", "booked"]):
                    logging.info("🎉 BOOKING LIKELY CONFIRMED!")
                    return True
                return False
        except Exception as e:
            logging.error(f"❌ Payment error: {e}")
            return False

    async def cleanup(self):
        try:
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
        except:
            pass


async def main():
    booker = FastCourtBooker()
    start_time = time.time()

    try:
        await booker.init_browser()

        if not await booker.login_first():
            logging.error("❌ Login failed!")
            return False

        booking_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=member"
        await booker.page.goto(booking_url)
        await asyncio.sleep(3)

        attempt = 0
        max_attempts = 200

        while attempt < max_attempts:
            attempt += 1
            elapsed = int(time.time() - start_time)
            logging.info(f"🔄 Attempt {attempt} (time: {elapsed}s)")

            if attempt % 20 == 0:
                if not await booker.check_login_status():
                    if not await booker.login_first(): break
                    await booker.page.goto(booking_url)

            if await booker.find_and_book_slot():
                logging.info(f"🎉 SUCCESS in {elapsed}s after {attempt} attempts!")
                return True
            else:
                await booker.page.reload()
                await asyncio.sleep(0.2)

        return False

    except Exception as e:
        logging.error(f"❌ Critical error: {e}")
        return False
    finally:
        await booker.cleanup()


if __name__ == "__main__":
    success = asyncio.run(main())
    logging.info("✅ Completed!" if success else "❌ Failed!")