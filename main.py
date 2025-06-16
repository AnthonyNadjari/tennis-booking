# Replace the find_and_book_slot function with this improved version:

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
        
        # Find all available slots
        available_slots = driver.find_elements(By.CSS_SELECTOR, "a.book-interval.not-booked")
        
        logging.info(f"📊 Total créneaux disponibles trouvés: {len(available_slots)}")
        
        if not available_slots:
            logging.warning("⚠️ Aucun créneau disponible trouvé")
            return False

        # Target time in minutes from midnight
        target_minutes = hour * 60 + minutes
        logging.info(f"🎯 Recherche créneaux pour {target_minutes} minutes ({hour_str})")
        
        # Look for slots matching our target time
        for i, slot in enumerate(available_slots):
            try:
                data_test_id = slot.get_attribute('data-test-id') or ""
                href = slot.get_attribute('href') or ""
                
                # Log slot details for debugging
                logging.info(f"   Slot {i+1}: data-test-id='{data_test_id}'")
                logging.info(f"   Slot {i+1}: href='{href}'")
                
                # Extract time from data-test-id (format: booking-xxxxx|date|minutes)
                if '|' in data_test_id:
                    parts = data_test_id.split('|')
                    if len(parts) >= 3:
                        try:
                            slot_minutes_int = int(parts[-1])  # Last part should be minutes
                            slot_hour = slot_minutes_int // 60
                            slot_min = slot_minutes_int % 60
                            slot_time_str = f"{slot_hour:02d}:{slot_min:02d}"
                            
                            logging.info(f"🕐 Slot {i+1}: {slot_time_str} ({slot_minutes_int} minutes)")
                            
                            # Check if this matches our target time
                            if slot_minutes_int == target_minutes:
                                logging.info(f"✅ CRÉNEAU TROUVÉ: {slot_time_str}")
                                
                                # **KEY FIX: Navigate to the slot's specific URL**
                                if href:
                                    logging.info(f"🔗 Navigation vers: {href}")
                                    driver.get(href)
                                    time.sleep(3)
                                    return complete_booking_process()
                                else:
                                    # Fallback: click the slot
                                    logging.info("🖱️ Fallback: clic sur le slot")
                                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", slot)
                                    time.sleep(1)
                                    driver.execute_script("arguments[0].click();", slot)
                                    time.sleep(2)
                                    return complete_booking_process()
                                    
                        except ValueError:
                            logging.warning(f"Impossible de convertir '{parts[-1]}' en minutes")
                            continue
                    
            except Exception as e:
                logging.warning(f"Erreur vérification slot {i+1}: {e}")
                continue

        # FALLBACK: Try text-based matching if exact time matching fails
        logging.info("🔍 Fallback: recherche par texte...")
        
        for i, slot in enumerate(available_slots):
            try:
                slot_text = slot.text.strip()
                inner_html = slot.get_attribute('innerHTML') or ""
                href = slot.get_attribute('href') or ""
                
                # Check for time patterns
                time_patterns = [
                    hour_str,  # 07:00
                    f"{hour}:{minutes:02d}",  # 7:00
                    f"{hour:02d}.{minutes:02d}",  # 07.00
                    f"{hour:02d}{minutes:02d}",  # 0700
                ]
                
                time_found = False
                for pattern in time_patterns:
                    if pattern in slot_text or pattern in inner_html:
                        time_found = True
                        break
                
                if time_found:
                    logging.info(f"✅ CRÉNEAU TROUVÉ (fallback): {slot_text}")
                    
                    # **KEY FIX: Use the slot's URL if available**
                    if href:
                        logging.info(f"🔗 Navigation vers: {href}")
                        driver.get(href)
                        time.sleep(3)
                        return complete_booking_process()
                    else:
                        # Fallback: click the slot
                        logging.info("🖱️ Fallback: clic sur le slot")
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", slot)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", slot)
                        time.sleep(2)
                        return complete_booking_process()
                    
            except Exception as e:
                logging.warning(f"Erreur fallback slot {i+1}: {e}")
                continue

        logging.warning(f"⚠️ Aucun créneau trouvé pour {hour_str}")
        return False

    except Exception as e:
        logging.error(f"❌ Erreur find_and_book_slot: {e}")
        take_screenshot("find_slot_error")
        return False


# Also, modify the main execution part to be more flexible with URLs:

# Main execution
try:
    start_time = time.time()
    max_duration = 300  # 5 minutes max
    
    # Navigate to booking page (more flexible URL)
    base_url = f"https://clubspark.lta.org.uk/SouthwarkPark/Booking/BookByDate"
    url = f"{base_url}#?date={date}&role=guest"
    logging.info(f"🌐 Navigation: {url}")
    driver.get(url)
    time.sleep(3)
    take_screenshot("initial_page")

    # Login first
    login_success = login_first(username, password)
    is_logged_in = login_success
    
    if login_success:
        logging.info("✅ Login réussi - Mode optimisé activé")
        # After login, navigate back to booking page
        driver.get(url)
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
                # Go back to the main booking page for refresh
                driver.get(url)
                time.sleep(3)
            else:
                break

    total_time = int(time.time() - start_time)
    logging.info(f"✅ Script terminé en {total_time}s après {attempt} tentatives")

except Exception as e:
    logging.error(f"❌ Erreur critique: {e}")
    take_screenshot("critical_error")
finally:
    driver.quit()
    logging.info("🏁 Driver fermé")
