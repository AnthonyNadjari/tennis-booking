import os
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import asyncio

# Configure logging
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
username = os.environ.get('TENNIS_USERNAME2') if account_number == '2' else os.environ.get('TENNIS_USERNAME')
password = os.environ.get('TENNIS_PASSWORD')
card_number = os.environ.get('CARD_NUMBER', '5354562794845156')
card_expiry = os.environ.get('CARD_EXPIRY', '04/30')
card_cvc = os.environ.get('CARD_CVC', '666')
date = os.environ.get('BOOKING_DATE', '2025-06-16')
hour = int(os.environ.get('BOOKING_HOUR', '7'))
minutes = int(os.environ.get('BOOKING_MINUTES', '0'))

if not username or not password:
    logging.error("❌ Username or password not defined!")
    exit(1)

total_minutes = (hour * 60) + minutes
hour_system_minutes = total_minutes
hour_str = f"{hour:02d}:{minutes:02d}"

logging.info(f"🎾 Booking for {date} at {hour_str}")
logging.info(f"⏰ System minutes: {hour_system_minutes}")
logging.info(f"👤 Account: {account_number} ({'Primary' if account_number == '1' else 'Secondary'})")


async def take_screenshot(page, name):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{name}_{timestamp}.png"
        await page.screenshot(path=filename)
        logging.info(f"📸 Screenshot saved: {filename}")
    except Exception as e:
        logging.error(f"Screenshot error: {e}")


async def check_login_status(page):
    try:
        content = await page.content()
        logged_in_indicators = ["My bookings", "Log out", "Sign out", "My account", "Account settings"]
        return any(indicator in content for indicator in logged_in_indicators)
    except:
        return False


async def ensure_logged_in(page, username, password):
    if await check_login_status(page):
        logging.info("✅ Already logged in!")
        return True
    logging.info("🔐 Not logged in, attempting to log in...")
    return await login_first(page, username, password)


async def login_first(page, username, password):
    try:
        logging.info("🔐 Starting full login process...")
        await page.goto("https://clubspark.lta.org.uk/SouthwarkPark")
        await page.wait_for_timeout(2000)

        try:
            await page.click(".osano-cm-accept-all")
            logging.info("✅ Cookies accepted")
            await page.wait_for_timeout(1000)
        except Exception as e:
            logging.warning(f"Cookie acceptance button not found: {e}")

        try:
            await page.click("a:has-text('Sign in')")
            logging.info("✅ Clicked on Sign in")
            await page.wait_for_timeout(2000)
        except Exception as e:
            logging.warning(f"Sign in link not found: {e}")
            await page.goto("https://clubspark.lta.org.uk/SouthwarkPark/Account/Login")
            await page.wait_for_timeout(2000)

        try:
            await page.click("button:has-text('Login')")
            logging.info("✅ Clicked on Login")
            await page.wait_for_timeout(2000)
        except Exception as e:
            logging.warning(f"Login button not found: {e}")

        try:
            await page.fill("input[name='username']", username)
            logging.info("✅ Username entered")

            await page.fill("input[name='password']", password)
            logging.info("✅ Password entered")

            await page.click("button:has-text('Log in')")
            logging.info("✅ Login submitted")
            await page.wait_for_timeout(3000)

            if await check_login_status(page):
                logging.info("✅ Login confirmed!")
                return True
            else:
                logging.error("❌ Login not confirmed")
                await take_screenshot(page, "login_failed")
                return False
        except Exception as e:
            logging.error(f"Error entering credentials: {e}")
            await take_screenshot(page, "login_error")
            return False

    except Exception as e:
        logging.error(f"❌ Login error: {e}")
        await take_screenshot(page, "login_error")
        return False


async def find_and_book_slot(page):
    try:
        if not await check_login_status(page):
            logging.warning("⚠️ Session lost, need to reconnect")
            return False

        try:
            await page.click(".osano-cm-accept-all")
        except:
            pass

        target_time_minutes = hour * 60 + minutes
        xpath_query = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{target_time_minutes}')]"

        try:
            await page.click(f"xpath={xpath_query}")
            logging.info(f"🎯 SLOT FOUND DIRECTLY at {hour_str}!")
            await page.wait_for_timeout(1000)
            return await complete_booking_process(page)
        except:
            logging.info("⚠️ Direct search failed, using classic method...")

            booking_links = await page.query_selector_all("a.book-interval.not-booked")
            for link in booking_links:
                data_test_id = await link.get_attribute('data-test-id') or ""
                if '|' in data_test_id:
                    parts = data_test_id.split('|')
                    if len(parts) >= 3 and int(parts[2]) == target_time_minutes:
                        logging.info(f"🎯 SLOT FOUND at {hour_str}!")
                        await link.click()
                        await page.wait_for_timeout(1000)
                        return await complete_booking_process(page)

        logging.warning(f"⚠️ No slot found for {hour_str}")
        return False
    except Exception as e:
        logging.error(f"❌ Error: {e}")
        return False


async def complete_booking_process(page):
    try:
        if not await check_login_status(page):
            logging.error("❌ Redirect to login after selecting slot!")
            return False

        try:
            await page.click(".select2-selection--single")
            options = await page.query_selector_all(".select2-results__option")
            if len(options) >= 2:
                await options[1].click()
        except Exception as e:
            logging.warning(f"Could not select duration: {e}")

        try:
            await page.click("button:has-text('Continue')")
        except Exception as e:
            logging.error(f"Continue button not found: {e}")
            return False

        if not await check_login_status(page):
            logging.error("❌ Redirect to login after Continue!")
            return False

        try:
            await page.click("#paynow")
            return await handle_stripe_payment(page)
        except:
            logging.error("❌ Payment button not found")
            return False

    except Exception as e:
        logging.error(f"❌ Booking error: {e}")
        return False


async def handle_stripe_payment(page):
    try:
        logging.info("💳 Handling Stripe payment...")

        if "login" in page.url.lower():
            logging.error("❌ On login page instead of Stripe!")
            return False

        iframes = await page.query_selector_all("iframe[name^='__privateStripeFrame']")
        if len(iframes) < 3:
            logging.error("❌ Not enough Stripe iframes")
            return False

        await iframes[0].frame_locator("input[name='cardnumber']").fill(card_number)
        await iframes[1].frame_locator("input[name='exp-date']").fill(card_expiry)
        await iframes[2].frame_locator("input[name='cvc']").fill(card_cvc)

        await page.click("#cs-stripe-elements-submit-button")

        try:
            await page.wait_for_url("**/confirmation**", timeout=20000)
            logging.info("🎉 BOOKING CONFIRMED!")
            return True
        except:
            content = await page.content()
            if any(word in content.lower() for word in ["confirmed", "success", "booked", "reserved", "confirmation"]):
                logging.info("🎉 BOOKING PROBABLY CONFIRMED!")
                return True
            else:
                logging.error("❌ No confirmation found")
                return False

    except Exception as e:
        logging.error(f"❌ Stripe payment error: {e}")
        return False


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        start_time = datetime.now()
        max_duration = 300

        if not await login_first(page, username, password):
            logging.error("❌ Unable to log in!")
            return

        booking_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=member"
        await page.goto(booking_url)
        await page.wait_for_timeout(2000)

        if not await check_login_status(page):
            logging.error("❌ Session lost after navigation!")
            return

        attempt = 0
        max_attempts = 300

        while attempt < max_attempts and (datetime.now() - start_time).seconds < max_duration:
            attempt += 1
            if attempt % 10 == 0 and not await check_login_status(page):
                if not await login_first(page, username, password):
                    logging.error("❌ Reconnection failed!")
                    break
                await page.goto(booking_url)
                await page.wait_for_timeout(1000)

            logging.info(f"🔄 Attempt {attempt}/{max_attempts} (time: {(datetime.now() - start_time).seconds}s)")

            if await find_and_book_slot(page):
                logging.info("🎉 BOOKING SUCCESSFUL!")
                break
            else:
                await page.reload()
                await page.wait_for_timeout(200)

        logging.info(f"✅ Script finished after {(datetime.now() - start_time).seconds}s and {attempt} attempts")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())