from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import logging
from datetime import datetime
import re

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('booking.log'),
        logging.StreamHandler()
    ]
)

# Configuration Chrome
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

# Variables d'environnement
account_number = os.environ.get('ACCOUNT', '1')
if account_number == '2':
    username = os.environ.get('TENNIS_USERNAME2')
    logging.info("🔑 Utilisation du compte secondaire (TENNIS_USERNAME2)")
else:
    username = os.environ.get('TENNIS_USERNAME')
    logging.info("🔑 Utilisation du compte principal (TENNIS_USERNAME)")

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

# Calculate total minutes and format display
total_minutes = (hour * 60) + minutes
hour_system_minutes = total_minutes
hour_str = f"{hour:02d}:{minutes:02d}"

logging.info(f"🎾 Réservation pour le {date} à {hour_str}")
logging.info(f"⏰ Minutes système: {hour_system_minutes}")
logging.info(f"👤 Compte: {account_number} ({'Principal' if account_number == '1' else 'Secondaire'})")

# Initialize driver - GLOBAL VARIABLE
driver = None

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_size(1920, 1080)
    logging.info("✅ Driver initialisé")
except Exception as e:
    logging.error(f"❌ Erreur driver: {e}")
    exit(1)

def take_screenshot(name):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{name}_{timestamp}.png"
        driver.save_screenshot(filename)
        logging.info(f"📸 Screenshot: {filename}")
    except Exception as e:
        logging.error(f"Erreur screenshot: {e}")

def login_first(username, password):
    try:
        # Check if already logged in
        current_page = driver.page_source
        if "My bookings" in current_page or "Log out" in current_page:
            logging.info("✅ Déjà connecté!")
            return True

        logging.info("🔐 Processus de connexion...")
        
        # Step 1: Click Sign in
        try:
            sign_in_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in') or contains(@href, 'login')]"))
            )
            sign_in_link.click()
            logging.info("✅ Cliqué sur Sign in")
            time.sleep(1)
        except Exception as e:
            logging.warning(f"Sign in non trouvé: {e}")

        # Step 2: Click Login button
        try:
            login_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Log in')]"))
            )
            login_btn.click()
            logging.info("✅ Cliqué sur Login")
            time.sleep(1)
        except Exception as e:
            logging.warning(f"Login button non trouvé: {e}")

        # Step 3: Fill credentials
        try:
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Username' or @name='username' or @id='username']"))
            )
            username_field.clear()
            username_field.send_keys(username)
            logging.info("✅ Username saisi")

            password_field = driver.find_element(By.XPATH, "//input[@placeholder='Password' or @name='password' or @id='password' or @type='password']")
            password_field.clear()
            password_field.send_keys(password)
            logging.info("✅ Password saisi")

            # Submit login
            submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Login') or @type='submit']")
            submit_btn.click()
            logging.info("✅ Login soumis")
            
            time.sleep(2)
            return True

        except Exception as e:
            logging.error(f"Erreur saisie credentials: {e}")
            return False

    except Exception as e:
        logging.error(f"❌ Erreur login: {e}")
        take_screenshot("login_error")
        return False

def wait_for_page_load():
    """Wait for the booking page to fully load"""
    try:
        # Wait for the main booking grid to be present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.resource-session, div.resource, .booking-grid, .session-container, .sessions-container"))
        )
        
        # Wait a bit more for dynamic content to load
        time.sleep(3)
        
        # Wait for booking elements - more flexible selectors
        WebDriverWait(driver, 5).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "a.book-interval, div.session-break, .available-booking-slot, a[href*='booking'], .not-booked")) > 0
        )
        
        logging.info("✅ Page de réservation chargée")
        return True
    except TimeoutException:
        logging.warning("⚠️ Timeout lors du chargement de la page")
        return False

def find_and_book_slot():
    try:
        # Accept cookies first
        try:
            cookie_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "osano-cm-accept-all"))
            )
            cookie_btn.click()
            logging.info("✅ Cookies acceptés")
            time.sleep(0.5)
        except:
            pass

        # Wait for page to load completely
        if not wait_for_page_load():
            logging.error("❌ Page non chargée correctement")
            return False

        logging.info(f"🔍 Recherche créneaux disponibles à {hour_str}...")
        
        # First, let's understand the page structure better
        # Look for price elements which indicate available slots
        price_selectors = [
            "td:contains('£')",  # Table cells containing price
            "div:contains('£')",  # Divs containing price
            "*:contains('£3.60')",  # Any element with the standard price £3.60
            "*:contains('£4.95')",  # Any element with the higher price £4.95
            ".price",  # Elements with price class
            "[class*='price']"  # Elements with price in class name
        ]
        
        # Find all elements that might be bookable slots
        all_potential_slots = []
        
        # Method 1: Find links in table cells or divs that are in the same row as our target time
        try:
            # Find the row containing our target time
            time_text_variations = [
                f"{hour:02d}:{minutes:02d}",  # 11:00
                f"{hour}:{minutes:02d}",       # 11:00 (without leading zero)
                f"{hour:02d}.{minutes:02d}",   # 11.00
                f"{hour}h{minutes:02d}" if minutes > 0 else f"{hour}h"  # 11h00 or 11h
            ]
            
            for time_text in time_text_variations:
                # Find elements containing our time
                time_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{time_text}')]")
                logging.info(f"🕐 Found {len(time_elements)} elements with time text '{time_text}'")
                
                for time_elem in time_elements:
                    # Look for slots in the same row (tr) or nearby containers
                    try:
                        # Find parent row if in a table
                        parent_row = time_elem.find_element(By.XPATH, "./ancestor::tr")
                        # Find all links or clickable elements in this row
                        row_links = parent_row.find_elements(By.CSS_SELECTOR, "a, td[onclick], div[onclick]")
                        
                        for link in row_links:
                            # Check if it's an available slot (has price or not marked as booked)
                            link_text = link.text.strip()
                            link_html = link.get_attribute('innerHTML') or ""
                            
                            if ('£' in link_text or '£' in link_html) and 'booked' not in link_text.lower():
                                all_potential_slots.append(link)
                                logging.info(f"✅ Found potential slot in row: {link_text}")
                    except:
                        pass
                    
                    # Also look for adjacent cells/divs
                    try:
                        following_cells = time_elem.find_elements(By.XPATH, "./following::td[position()<=4] | ./following::div[position()<=4]")
                        for cell in following_cells:
                            cell_links = cell.find_elements(By.TAG_NAME, "a")
                            for link in cell_links:
                                if '£' in link.text or '£' in cell.text:
                                    all_potential_slots.append(link)
                                    logging.info(f"✅ Found potential adjacent slot: {link.text}")
                    except:
                        pass
        except Exception as e:
            logging.warning(f"Erreur recherche par ligne: {e}")
        
        # Method 2: Find all slots with prices
        try:
            # Look for any element containing a price that is also a link
            price_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '£')]")
            logging.info(f"💰 Found {len(price_elements)} price elements")
            
            for price_elem in price_elements:
                # Check if it's a link or has a parent link
                if price_elem.tag_name == 'a':
                    all_potential_slots.append(price_elem)
                else:
                    parent_links = price_elem.find_elements(By.XPATH, "./ancestor::a")
                    if parent_links:
                        all_potential_slots.append(parent_links[0])
                    else:
                        # Check if the price element itself is clickable
                        onclick = price_elem.get_attribute('onclick')
                        if onclick:
                            all_potential_slots.append(price_elem)
        except Exception as e:
            logging.warning(f"Erreur recherche prix: {e}")
        
        # Method 3: Original selectors (fallback)
        selectors = [
            "a.book-interval.not-booked",
            "a.book-interval:not(.booked)",
            "a[href*='booking']:not(.booked)",
            ".not-booked a",
            "a.available-booking-slot",
            "td a[href*='booking']",  # Links in table cells
            "td[onclick]",  # Clickable table cells
        ]
        
        for selector in selectors:
            try:
                slots = driver.find_elements(By.CSS_SELECTOR, selector)
                if slots:
                    all_potential_slots.extend(slots)
                    logging.info(f"✅ Trouvé {len(slots)} créneaux avec selector: {selector}")
            except:
                pass
        
        # Remove duplicates and filter
        unique_slots = []
        seen_elements = set()
        
        for slot in all_potential_slots:
            try:
                # Create a unique identifier for the element
                elem_id = f"{slot.location['x']}_{slot.location['y']}_{slot.size['width']}_{slot.size['height']}"
                if elem_id not in seen_elements:
                    seen_elements.add(elem_id)
                    # Only add if it's not marked as booked
                    slot_text = slot.text.strip().lower()
                    if 'booked' not in slot_text and slot.is_displayed():
                        unique_slots.append(slot)
            except:
                pass
        
        logging.info(f"📊 Total créneaux uniques potentiels: {len(unique_slots)}")
        
        if not unique_slots:
            logging.warning("⚠️ Aucun créneau disponible trouvé")
            # Debug: log page structure
            all_tds = driver.find_elements(By.TAG_NAME, "td")[:20]
            logging.info(f"🔍 Premières cellules de tableau:")
            for i, td in enumerate(all_tds):
                logging.info(f"   TD {i}: text='{td.text.strip()}', onclick='{td.get_attribute('onclick')}'")
            return False
        
        # Now check each unique slot to see if it's for our target time
        target_minutes = hour * 60 + minutes
        logging.info(f"🎯 Vérification des {len(unique_slots)} créneaux pour {hour_str}")
        
        for i, slot in enumerate(unique_slots):
            try:
                # Get slot information
                slot_text = slot.text.strip()
                href = slot.get_attribute('href') or ""
                onclick = slot.get_attribute('onclick') or ""
                parent_row_text = ""
                
                # Try to get the time from the parent row
                try:
                    parent_row = slot.find_element(By.XPATH, "./ancestor::tr")
                    parent_row_text = parent_row.text
                except:
                    pass
                
                logging.info(f"   Slot {i+1}: text='{slot_text}', row='{parent_row_text[:50]}...'")
                
                # Check if this slot is in the correct time row
                time_found = False
                for time_text in [f"{hour:02d}:{minutes:02d}", f"{hour}:{minutes:02d}", f"{hour:02d}.{minutes:02d}"]:
                    if time_text in parent_row_text:
                        time_found = True
                        logging.info(f"✅ Slot trouvé pour {time_text}!")
                        break
                
                if time_found and ('£' in slot_text or '£' in parent_row_text):
                    logging.info(f"🎯 CRÉNEAU DISPONIBLE TROUVÉ à {hour_str}!")
                    
                    # Try to book this slot
                    try:
                        # Scroll to element
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", slot)
                        time.sleep(1)
                        
                        # Try clicking
                        if href:
                            logging.info(f"🔗 Navigation vers: {href}")
                            driver.get(href)
                        elif onclick:
                            logging.info(f"🖱️ Execution onclick: {onclick}")
                            driver.execute_script(onclick)
                        else:
                            logging.info("🖱️ Clic direct sur l'élément")
                            try:
                                slot.click()
                            except:
                                driver.execute_script("arguments[0].click();", slot)
                        
                        time.sleep(3)
                        
                        # Check if we moved to a booking page
                        if 'booking' in driver.current_url.lower() or 'reserve' in driver.current_url.lower():
                            return complete_booking_process()
                        else:
                            logging.warning("⚠️ Pas redirigé vers la page de réservation")
                            
                    except Exception as e:
                        logging.error(f"Erreur lors du clic: {e}")
                        continue
                        
            except Exception as e:
                logging.warning(f"Erreur vérification slot {i+1}: {e}")
                continue
        
        logging.warning(f"⚠️ Aucun créneau disponible trouvé pour {hour_str}")
        
        # Take a screenshot for debugging
        take_screenshot("no_slots_found")
        
        return False

    except Exception as e:
        logging.error(f"❌ Erreur find_and_book_slot: {e}")
        take_screenshot("find_slot_error")
        return False

def complete_booking_process():
    try:
        take_screenshot("booking_form")
        
        # Wait for booking form to load
        time.sleep(2)
        
        # Check if we're on a booking page
        current_url = driver.current_url
        page_source = driver.page_source.lower()
        
        if 'booking' not in current_url.lower() and 'booking' not in page_source:
            logging.warning("⚠️ Pas sur une page de réservation")
            return False
        
        # Select duration if needed
        try:
            # Try Select2 dropdown first
            select2_dropdown = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".select2-selection, .select2-selection--single"))
            )
            select2_dropdown.click()
            time.sleep(0.5)
            
            # Select 1 hour option (usually second option)
            options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
            if len(options) >= 2:
                options[1].click()
                logging.info("✅ Durée sélectionnée (Select2)")
            
        except:
            # Fallback to regular select
            try:
                duration_select = driver.find_element(By.ID, "booking-duration")
                Select(duration_select).select_by_index(1)
                logging.info("✅ Durée sélectionnée (select)")
            except:
                logging.info("⚠️ Pas de sélection durée nécessaire")

        time.sleep(1)

        # Click Continue
        continue_clicked = False
        continue_selectors = [
            "//button[contains(text(), 'Continue')]",
            "//button[contains(text(), 'Next')]",
            "//button[contains(text(), 'Suivant')]",
            "//input[@type='submit' and contains(@value, 'Continue')]",
            "//a[contains(text(), 'Continue')]",
            "//button[@type='submit']"
        ]
        
        for selector in continue_selectors:
            try:
                continue_btn = driver.find_element(By.XPATH, selector)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continue_btn)
                time.sleep(0.5)
                continue_btn.click()
                logging.info(f"✅ Continue cliqué avec: {selector}")
                continue_clicked = True
                time.sleep(2)
                break
            except:
                continue

        if not continue_clicked:
            logging.error("❌ Bouton Continue non trouvé")
            return False

        # Click Pay Now
        pay_clicked = False
        pay_selectors = [
            (By.ID, "paynow"),
            (By.XPATH, "//button[contains(text(), 'Pay')]"),
            (By.XPATH, "//button[contains(text(), 'Payer')]"),
            (By.XPATH, "//input[@type='submit' and contains(@value, 'Pay')]"),
            (By.XPATH, "//a[contains(text(), 'Pay')]")
        ]
        
        for by, selector in pay_selectors:
            try:
                pay_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((by, selector))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pay_btn)
                time.sleep(0.5)
                pay_btn.click()
                logging.info(f"✅ Pay Now cliqué avec: {selector}")
                pay_clicked = True
                time.sleep(2)
                break
            except:
                continue

        if not pay_clicked:
            logging.error("❌ Bouton Pay Now non trouvé")
            return False

        # Handle Stripe payment
        return handle_stripe_payment()

    except Exception as e:
        logging.error(f"❌ Erreur complete_booking_process: {e}")
        take_screenshot("booking_process_error")
        return False

def handle_stripe_payment():
    try:
        logging.info("💳 Traitement paiement Stripe...")
        take_screenshot("stripe_form")
        
        # Wait for Stripe iframes to load
        iframes = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[name^='__privateStripeFrame']"))
        )
        logging.info(f"✅ {len(iframes)} iframes Stripe trouvées")

        if len(iframes) < 3:
            logging.error("❌ Pas assez d'iframes Stripe")
            return False

        # Card number
        driver.switch_to.frame(iframes[0])
        card_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cardnumber'], input[placeholder*='card'], input[data-elements-stable-field-name='cardNumber']"))
        )
        card_field.clear()
        card_field.send_keys(card_number)
        driver.switch_to.default_content()
        logging.info("✅ Numéro carte saisi")

        # Expiry date
        driver.switch_to.frame(iframes[1])
        expiry_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='exp-date'], input[placeholder*='MM'], input[data-elements-stable-field-name='cardExpiry']"))
        )
        expiry_field.clear()
        expiry_field.send_keys(card_expiry)
        driver.switch_to.default_content()
        logging.info("✅ Date expiration saisie")

        # CVC
        driver.switch_to.frame(iframes[2])
        cvc_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='cvc'], input[placeholder*='CVC'], input[data-elements-stable-field-name='cardCvc']"))
        )
        cvc_field.clear()
        cvc_field.send_keys(card_cvc)
        driver.switch_to.default_content()
        logging.info("✅ CVC saisi")

        # Submit payment
        submit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "cs-stripe-elements-submit-button"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(0.5)
        submit_btn.click()
        logging.info("✅ Paiement soumis")

        # Wait for confirmation
        try:
            WebDriverWait(driver, 30).until(
                lambda d: "confirmation" in d.current_url.lower() or "success" in d.current_url.lower()
            )
            take_screenshot("confirmation")
            logging.info("🎉 RÉSERVATION CONFIRMÉE!")
            return True
        except:
            # Check for any success indicators on page
            time.sleep(5)
            page_source = driver.page_source.lower()
            if any(word in page_source for word in ["confirmed", "success", "booked", "reserved", "confirmation"]):
                logging.info("🎉 RÉSERVATION PROBABLEMENT CONFIRMÉE!")
                take_screenshot("probable_success")
                return True
            else:
                logging.error("❌ Pas de confirmation trouvée")
                return False

    except Exception as e:
        logging.error(f"❌ Erreur paiement Stripe: {e}")
        take_screenshot("stripe_error")
        return False

# Main execution
try:
    start_time = time.time()
    max_duration = 300  # 5 minutes max
    
    # Navigate to booking page - try different URL formats
    base_urls = [
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate#?date={date}&role=guest",
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate?date={date}",
        f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/Calendar?date={date}",
        "https://clubspark.lta.org.uk/SouthwarkPark/Booking"
    ]
    
    url_success = False
    for url in base_urls:
        try:
            logging.info(f"🌐 Essai navigation: {url}")
            driver.get(url)
            time.sleep(3)
            
            # Check if we're on a booking page
            if "booking" in driver.current_url.lower() or "calendar" in driver.current_url.lower():
                url_success = True
                logging.info(f"✅ URL réussie: {url}")
                break
        except:
            continue
    
    if not url_success:
        logging.error("❌ Impossible de naviguer vers la page de réservation")
        exit(1)
    
    take_screenshot("initial_page")

    # Login first
    login_success = login_first(username, password)
    is_logged_in = login_success
    
    if login_success:
        logging.info("✅ Login réussi - Mode optimisé activé")
        # After login, navigate back to booking page
        driver.get(base_urls[0])
        time.sleep(3)
    else:
        logging.warning("⚠️ Login échoué, on continue...")
    
    # Try booking with optimized retry loop
    attempt = 0
    max_attempts = 300 if is_logged_in else 10
    
    while attempt < max_attempts and (time.time() - start_time) < max_duration:
        attempt += 1
        elapsed = int(time.time() - start_time)
        logging.info(f"🔄 Tentative {attempt}/{max_attempts} (temps: {elapsed}s)")
        
        if find_and_book_slot():
            logging.info("🎉 RÉSERVATION RÉUSSIE!")
            break
        else:
            if attempt < max_attempts and (time.time() - start_time) < max_duration - 10:
                refresh_delay = 1.5 if is_logged_in else 3.0
                logging.info(f"⏳ Actualisation dans {refresh_delay}s...")
                time.sleep(refresh_delay)
                # Refresh the page
                driver.refresh()
                time.sleep(2)
            else:
                break

    total_time = int(time.time() - start_time)
    logging.info(f"✅ Script terminé en {total_time}s après {attempt} tentatives")

except Exception as e:
    logging.error(f"❌ Erreur critique: {e}")
    if driver:
        take_screenshot("critical_error")
finally:
    if driver:
        driver.quit()
        logging.info("🏁 Driver fermé")
