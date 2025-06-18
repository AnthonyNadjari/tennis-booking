import asyncio
from playwright.async_api import async_playwright
import time
import os
import logging
from datetime import datetime
import re

# Configuration du logging

logging.basicConfig(
level=logging.INFO,
format=’%(asctime)s - %(levelname)s - %(message)s’,
handlers=[
logging.FileHandler(‘booking.log’),
logging.StreamHandler()
]
)

# Variables d’environnement

account_number = os.environ.get(‘ACCOUNT’, ‘1’)
if account_number == ‘2’:
username = os.environ.get(‘TENNIS_USERNAME2’)
logging.info(“🔑 Utilisation du compte secondaire (TENNIS_USERNAME2)”)
else:
username = os.environ.get(‘TENNIS_USERNAME’)
logging.info(“🔑 Utilisation du compte principal (TENNIS_USERNAME)”)

password = os.environ.get(‘TENNIS_PASSWORD’)
card_number = os.environ.get(‘CARD_NUMBER’, ‘5354562794845156’)
card_expiry = os.environ.get(‘CARD_EXPIRY’, ‘04/30’)
card_cvc = os.environ.get(‘CARD_CVC’, ‘666’)
date = os.environ.get(‘BOOKING_DATE’, ‘2025-06-16’)
hour = int(os.environ.get(‘BOOKING_HOUR’, ‘7’))
minutes = int(os.environ.get(‘BOOKING_MINUTES’, ‘0’))

if not username or not password:
logging.error(“❌ Username ou password non définis!”)
exit(1)

# Calculate total minutes and format display

total_minutes = (hour * 60) + minutes
hour_system_minutes = total_minutes
hour_str = f”{hour:02d}:{minutes:02d}”

logging.info(f”🎾 Réservation pour le {date} à {hour_str}”)
logging.info(f”⏰ Minutes système: {hour_system_minutes}”)
logging.info(f”👤 Compte: {account_number} ({‘Principal’ if account_number == ‘1’ else ‘Secondaire’})”)
logging.info(f”📸 Les screenshots seront sauvegardés dans le répertoire courant”)

# Global variables

page = None

async def take_screenshot(name):
try:
timestamp = datetime.now().strftime(”%Y%m%d_%H%M%S”)
filename = f”screenshot_{name}_{timestamp}.png”
await page.screenshot(path=filename, full_page=True)
logging.info(f”📸 Screenshot sauvegardé: {filename}”)
except Exception as e:
logging.error(f”Erreur screenshot: {e}”)

async def check_login_status():
“”“Check if we’re currently logged in”””
try:
content = await page.content()
# Multiple indicators of being logged in
logged_in_indicators = [“My bookings”, “Log out”, “Sign out”, “My account”, “Account settings”]

```
    for indicator in logged_in_indicators:
        if indicator in content:
            return True
    
    # Check for login form as negative indicator
    current_url = page.url
    if "username" in content.lower() and "password" in content.lower():
        if "login" in current_url.lower() or "signin" in current_url.lower():
            return False
    
    return False
except:
    return False
```

async def ensure_logged_in():
“”“Ensure we’re logged in, login if not”””
if await check_login_status():
logging.info(“✅ Déjà connecté!”)
return True

```
logging.info("🔐 Pas connecté, tentative de connexion...")
return await login_first()
```

async def login_first():
try:
logging.info(“🔐 Processus de connexion complet…”)

```
    # Navigate to main page first
    await page.goto("https://clubspark.lta.org.uk/SouthwarkPark", wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)
    
    # Accept cookies if present
    try:
        await page.click(".osano-cm-accept-all", timeout=1000)
        await page.wait_for_timeout(500)
    except:
        pass

    # Step 1: Click Sign in
    try:
        await page.click("a:has-text('Sign in'), a[href*='login']", timeout=10000)
        logging.info("✅ Cliqué sur Sign in")
        await page.wait_for_timeout(2000)
    except Exception as e:
        logging.warning(f"Sign in non trouvé: {e}")
        # Try direct navigation to login
        await page.goto("https://clubspark.lta.org.uk/SouthwarkPark/Account/Login", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

    # Step 2: Click Login button if needed
    try:
        await page.click("button:has-text('Login'), button:has-text('Log in')", timeout=5000)
        logging.info("✅ Cliqué sur Login")
        await page.wait_for_timeout(2000)
    except:
        pass

    # Step 3: Fill credentials
    try:
        # Wait for form to be present
        await page.wait_for_selector("input[placeholder*='Username'], input[name='username'], input[id='username']", timeout=10000)
        
        await page.fill("input[placeholder*='Username'], input[name='username'], input[id='username']", username)
        logging.info("✅ Username saisi")

        await page.fill("input[placeholder*='Password'], input[name='password'], input[id='password'], input[type='password']", password)
        logging.info("✅ Password saisi")

        # Submit login
        await page.click("button:has-text('Log in'), button:has-text('Login'), button[type='submit']")
        logging.info("✅ Login soumis")

        # Wait for login to complete
        await page.wait_for_timeout(3000)
        
        # Verify login succeeded
        if await check_login_status():
            logging.info("✅ Login confirmé!")
            return True
        else:
            logging.error("❌ Login non confirmé")
            await take_screenshot("login_failed")
            return False

    except Exception as e:
        logging.error(f"Erreur saisie credentials: {e}")
        await take_screenshot("login_error")
        return False

except Exception as e:
    logging.error(f"❌ Erreur login: {e}")
    await take_screenshot("login_error")
    return False
```

async def wait_for_page_load():
“”“Wait for the booking page to fully load”””
try:
# Wait for booking links
await page.wait_for_selector(“a.book-interval”, timeout=5000)
await page.wait_for_timeout(300)

```
    # Check we're not on login page
    if "login" in page.url.lower():
        logging.error("❌ Redirigé vers la page de login!")
        return False
    
    logging.info("✅ Page de réservation chargée")
    return True
except:
    logging.warning("⚠️ Timeout lors du chargement de la page")
    return False
```

async def find_and_book_slot():
try:
# Check login status first
if not await check_login_status():
logging.warning(“⚠️ Session perdue, reconnexion nécessaire”)
return False

```
    # Accept cookies if needed
    try:
        await page.click(".osano-cm-accept-all", timeout=100)
    except:
        pass

    # Wait for page to load
    if not await wait_for_page_load():
        return False

    logging.info(f"🔍 Recherche créneaux à {hour_str}...")

    # Direct selector to find slot
    target_time_minutes = hour * 60 + minutes
    xpath_query = f"//a[@class='book-interval not-booked' and contains(@data-test-id, '|{target_time_minutes}')]"

    try:
        await page.click(f"xpath={xpath_query}", timeout=2000)
        logging.info(f"🎯 SLOT TROUVÉ DIRECTEMENT à {hour_str}!")
        await page.wait_for_timeout(1500)
        return await complete_booking_process()

    except:
        logging.info("⚠️ Recherche directe échouée, méthode classique...")

        booking_links = await page.query_selector_all("a.book-interval.not-booked")

        for link in booking_links:
            data_test_id = await link.get_attribute('data-test-id') or ""

            if '|' in data_test_id:
                parts = data_test_id.split('|')
                if len(parts) >= 3:
                    try:
                        if int(parts[2]) == target_time_minutes:
                            logging.info(f"🎯 SLOT TROUVÉ à {hour_str}!")
                            await link.click()
                            await page.wait_for_timeout(1500)
                            return await complete_booking_process()
                    except:
                        continue

    logging.warning(f"⚠️ Aucun slot trouvé pour {hour_str}")
    return False

except Exception as e:
    logging.error(f"❌ Erreur: {e}")
    return False
```

async def complete_booking_process():
try:
await page.wait_for_timeout(1000)

```
    # CRITICAL: Check we're still logged in after clicking slot
    current_url = page.url
    logging.info(f"📍 URL après clic slot: {current_url}")
    
    if "login" in current_url.lower() or not await check_login_status():
        logging.error("❌ Redirigé vers login après sélection du slot!")
        await take_screenshot("redirected_to_login")
        return False

    # Select duration
    try:
        await page.click(".select2-selection, .select2-selection--single")
        await page.wait_for_timeout(300)

        options = await page.query_selector_all(".select2-results__option")
        if len(options) >= 2:
            await options[1].click()
            logging.info("✅ Durée sélectionnée")
    except:
        try:
            await page.select_option("#booking-duration", index=1)
            logging.info("✅ Durée sélectionnée")
        except:
            pass

    await page.wait_for_timeout(500)

    # Click Continue
    try:
        await page.click("button:has-text('Continue')")
        logging.info("✅ Continue cliqué")
        await page.wait_for_timeout(2000)
    except:
        try:
            await page.click("button[type='submit']")
            logging.info("✅ Continue cliqué (submit)")
            await page.wait_for_timeout(2000)
        except:
            logging.error("❌ Bouton Continue non trouvé")
            return False

    # CRITICAL: Check again after Continue
    current_url = page.url
    logging.info(f"📍 URL après Continue: {current_url}")
    
    if "login" in current_url.lower():
        logging.error("❌ Redirigé vers login après Continue!")
        await take_screenshot("login_redirect_after_continue")
        
        # Try to re-login quickly
        if await login_first():
            logging.info("✅ Re-connecté avec succès")
            # Need to restart the booking process
            return False
        else:
            logging.error("❌ Impossible de se reconnecter")
            return False
    
    # Look for payment button
    try:
        await page.wait_for_selector("#paynow", timeout=10000)
        
        # Scroll to payment button and click
        await page.locator("#paynow").scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        
        await page.click("#paynow")
        logging.info("✅ Confirm and pay cliqué")
        await page.wait_for_timeout(2000)
        
        return await handle_stripe_payment()
        
    except:
        logging.error("❌ Bouton payment non trouvé")
        await take_screenshot("payment_button_not_found")
        
        # Log current page info
        title = await page.title()
        logging.info(f"🔍 Titre page: {title}")
        buttons = await page.query_selector_all("button")
        logging.info(f"🔘 {len(buttons)} boutons sur la page")
        
        return False

except Exception as e:
    logging.error(f"❌ Erreur booking: {e}")
    await take_screenshot("booking_error")
    return False
```

async def handle_stripe_payment():
try:
logging.info(“💳 Traitement paiement Stripe…”)

```
    # Check one more time we're not on login page
    if "login" in page.url.lower():
        logging.error("❌ Sur la page de login au lieu de Stripe!")
        return False
    
    await take_screenshot("stripe_form")

    # Wait for Stripe iframes
    await page.wait_for_selector("iframe[name^='__privateStripeFrame']", timeout=15000)
    iframes = await page.query_selector_all("iframe[name^='__privateStripeFrame']")
    logging.info(f"✅ {len(iframes)} iframes Stripe trouvées")

    if len(iframes) < 3:
        logging.error("❌ Pas assez d'iframes Stripe")
        return False

    # Fill payment details
    # Card number
    card_frame = page.frame_locator("iframe[name^='__privateStripeFrame']").nth(0)
    await card_frame.locator("input[name='cardnumber'], input[placeholder*='card'], input[data-elements-stable-field-name='cardNumber']").fill(card_number)
    logging.info("✅ Numéro carte saisi")

    # Expiry date
    expiry_frame = page.frame_locator("iframe[name^='__privateStripeFrame']").nth(1)
    await expiry_frame.locator("input[name='exp-date'], input[placeholder*='MM'], input[data-elements-stable-field-name='cardExpiry']").fill(card_expiry)
    logging.info("✅ Date expiration saisie")

    # CVC
    cvc_frame = page.frame_locator("iframe[name^='__privateStripeFrame']").nth(2)
    await cvc_frame.locator("input[name='cvc'], input[placeholder*='CVC'], input[data-elements-stable-field-name='cardCvc']").fill(card_cvc)
    logging.info("✅ CVC saisi")

    # Submit payment
    await page.locator("#cs-stripe-elements-submit-button").scroll_into_view_if_needed()
    await page.wait_for_timeout(500)
    await page.click("#cs-stripe-elements-submit-button")
    logging.info("✅ Paiement soumis")

    # Wait for confirmation
    try:
        await page.wait_for_url("**/confirmation**", timeout=30000)
        await take_screenshot("confirmation")
        logging.info("🎉 RÉSERVATION CONFIRMÉE!")
        return True
    except:
        await page.wait_for_timeout(5000)
        content = await page.content()
        content_lower = content.lower()
        if any(word in content_lower for word in ["confirmed", "success", "booked", "reserved", "confirmation"]):
            logging.info("🎉 RÉSERVATION PROBABLEMENT CONFIRMÉE!")
            await take_screenshot("probable_success")
            return True
        else:
            logging.error("❌ Pas de confirmation trouvée")
            return False

except Exception as e:
    logging.error(f"❌ Erreur paiement Stripe: {e}")
    await take_screenshot("stripe_error")
    return False
```

async def main():
global page

```
async with async_playwright() as p:
    # Launch browser with similar options to Selenium
    browser = await p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-blink-features=AutomationControlled"
        ]
    )
    
    # Create context with user agent
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080}
    )
    
    page = await context.new_page()
    
    try:
        start_time = time.time()
        max_duration = 300

        # Initial login
        logging.info("🔐 Connexion initiale...")
        login_success = await login_first()
        
        if not login_success:
            logging.error("❌ Impossible de se connecter!")
            return
        
        # Navigate to booking page after successful login
        booking_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=member"
        logging.info(f"🌐 Navigation vers: {booking_url}")
        await page.goto(booking_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        await take_screenshot("booking_page_after_login")
        
        # Verify we're still logged in
        if not await check_login_status():
            logging.error("❌ Session perdue après navigation!")
            return

        # Booking loop
        attempt = 0
        max_attempts = 300

        while attempt < max_attempts and (time.time() - start_time) < max_duration:
            attempt += 1
            elapsed = int(time.time() - start_time)
            
            # Check login status every 10 attempts
            if attempt % 10 == 0:
                if not await check_login_status():
                    logging.warning("⚠️ Session perdue, reconnexion...")
                    if not await login_first():
                        logging.error("❌ Reconnexion échouée!")
                        break
                    await page.goto(booking_url, wait_until="domcontentloaded")
                    await page.wait_for_timeout(2000)
            
            logging.info(f"🔄 Tentative {attempt}/{max_attempts} (temps: {elapsed}s)")

            if await find_and_book_slot():
                logging.info("🎉 RÉSERVATION RÉUSSIE!")
                break
            else:
                if attempt < max_attempts and (time.time() - start_time) < max_duration - 10:
                    # Fast refresh
                    await page.reload(wait_until="domcontentloaded")
                    # Small wait to avoid rate limiting
                    await page.wait_for_timeout(500)
                else:
                    break

        total_time = int(time.time() - start_time)
        logging.info(f"✅ Script terminé en {total_time}s après {attempt} tentatives")

    except Exception as e:
        logging.error(f"❌ Erreur critique: {e}")
        await take_screenshot("critical_error")
    finally:
        await browser.close()
        logging.info("🏁 Browser fermé")
```

if **name** == “**main**”:
asyncio.run(main())