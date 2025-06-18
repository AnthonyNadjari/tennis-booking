def complete_booking_process():
    try:
        # Minimal wait
        time.sleep(0.5)

        # Select duration quickly
        try:
            select2_dropdown = driver.find_element(By.CSS_SELECTOR, ".select2-selection, .select2-selection--single")
            select2_dropdown.click()
            time.sleep(0.2)

            options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
            if len(options) >= 2:
                options[1].click()
                logging.info("✅ Durée sélectionnée")
        except:
            try:
                duration_select = driver.find_element(By.ID, "booking-duration")
                Select(duration_select).select_by_index(1)
                logging.info("✅ Durée sélectionnée")
            except:
                pass

        time.sleep(0.3)

        # Click Continue - try the most common selector first
        try:
            continue_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
            continue_btn.click()
            logging.info("✅ Continue cliqué")
            time.sleep(1)
        except:
            # Quick fallback
            try:
                continue_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
                continue_btn.click()
                logging.info("✅ Continue cliqué (submit)")
                time.sleep(1)
            except:
                logging.error("❌ Bouton Continue non trouvé")
                return False

        # Click Confirm and pay - increased timeout and multiple strategies
        try:
            # First try by ID with longer timeout
            pay_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "paynow"))
            )
            
            # Scroll to button to ensure it's visible
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pay_btn)
            time.sleep(0.5)
            
            # Try JavaScript click if regular click might be intercepted
            try:
                pay_btn.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", pay_btn)
                
            logging.info("✅ Confirm and pay cliqué")
            time.sleep(1)
            
        except TimeoutException:
            # Fallback: try by button text
            try:
                pay_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Confirm and pay') or contains(text(), 'Pay')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pay_btn)
                time.sleep(0.5)
                pay_btn.click()
                logging.info("✅ Confirm and pay cliqué (par texte)")
                time.sleep(1)
            except:
                # Last resort: find any button with data-stripe-payment attribute
                try:
                    pay_btn = driver.find_element(By.CSS_SELECTOR, "button[data-stripe-payment='true']")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pay_btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", pay_btn)
                    logging.info("✅ Confirm and pay cliqué (data-stripe)")
                    time.sleep(1)
                except:
                    logging.error("❌ Bouton Confirm and pay non trouvé")
                    take_screenshot("pay_button_not_found")
                    # Log the page source to debug
                    logging.debug(f"Page source snippet: {driver.page_source[0:500]}")
                    return False

        # Handle Stripe payment
        return handle_stripe_payment()

    except Exception as e:
        logging.error(f"❌ Erreur booking: {e}")
        take_screenshot("booking_error")
        return False
