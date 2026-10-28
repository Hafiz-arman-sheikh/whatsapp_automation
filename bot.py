"""WhatsApp Web test-message sender. Excel: phone in column A, name in B.

Install dependencies: python -m pip install selenium webdriver-manager pandas openpyxl
Run: python bot.py
Only use with contacts who expect your messages.
"""

import random
import re
import time
import traceback
from pathlib import Path
from urllib.parse import quote

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


CONTACTS_FILE = Path(__file__).resolve().parent / "contacts.xlsx"
CHAT_TIMEOUT = 60
COMPOSER = (By.CSS_SELECTOR, 'footer div[contenteditable="true"][role="textbox"]')


def normalize_phone(value):
    phone = str(value).strip()
    if phone.endswith(".0"):
        phone = phone[:-2]
    phone = re.sub(r"[\s()\-]", "", phone)
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith("00"):
        phone = phone[2:]
    if not re.fullmatch(r"[1-9][0-9]{6,14}", phone):
        raise ValueError("Phone country code ke saath dein, misal: 923001234567.")
    return phone


def send_whatsapp_message(driver, phone_number, name):
    send_attempted = False
    try:
        message = (
            f"Assalam-o-Alaikum {name}! "
            "Yeh hamari Python automation script ka test message hai."
        )
        url = (
            "https://web.whatsapp.com/send"
            f"?phone={phone_number}&text={quote(message, safe='')}"
        )
        print(f"Opening chat for: {name} ({phone_number})")
        driver.get(url)

        wait = WebDriverWait(
            driver, CHAT_TIMEOUT,
            ignored_exceptions=(NoSuchElementException, StaleElementReferenceException),
        )
        wait.until(
            EC.element_to_be_clickable(COMPOSER),
            message="Chat ka message box nahi mila. Login/chat ya invalid-number popup check karein.",
        )

        def draft_is_ready(browser):
            box = browser.find_element(*COMPOSER)
            text = box.get_attribute("textContent") or ""
            return box if text.strip() == message else False

        box = wait.until(
            draft_is_ready,
            message="Message box mila, lekin expected prefilled message nahi aaya.",
        )
        box.click()
        # Set before sending: an exception here can leave the outcome uncertain.
        send_attempted = True
        box.send_keys(Keys.ENTER)

        def draft_is_empty(browser):
            composer = browser.find_element(*COMPOSER)
            return not (composer.get_attribute("textContent") or "").strip()

        wait.until(draft_is_empty, message="Enter ke baad composer clear nahi hua.")
        print(f"[OK] {name}: send action complete; composer clear.")
        return "completed"

    except Exception as error:
        status = "uncertain" if send_attempted else "failed"
        print(f"[{status.upper()}] {name}: {type(error).__name__}: {error}")
        traceback.print_exc()
        if send_attempted:
            print("Dobara bhejne se pehle WhatsApp chat check karein; duplicate ho sakta hai.")
        return status


def main():
    driver = None
    try:
        # Preserve phone numbers as text. Excel must have a header row.
        df = pd.read_excel(CONTACTS_FILE, dtype=str).fillna("")
        if df.shape[1] < 2:
            raise ValueError("contacts.xlsx mein column A phone aur column B name hona chahiye.")
        df = df.loc[~df.iloc[:, :2].eq("").all(axis=1)]
        if df.empty:
            print("contacts.xlsx mein koi contact nahi mila.")
            return

        options = webdriver.ChromeOptions()
        print("Chrome browser start ho raha hai...")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        driver.set_page_load_timeout(90)
        driver.get("https://web.whatsapp.com")
        input("WhatsApp Web scan karein. Chat list khulne ke baad yahan Enter dabayein...")

        counts = {"completed": 0, "failed": 0, "uncertain": 0}
        print(f"Total {len(df)} contacts mil gaye hain.")
        for position, (index, row) in enumerate(df.iterrows()):
            try:
                phone = normalize_phone(row.iloc[0])
            except ValueError as error:
                print(f"[SKIP] Excel row {index + 2}: {error}")
                counts["failed"] += 1
                continue

            name = str(row.iloc[1]).strip() or "Dost"
            status = send_whatsapp_message(driver, phone, name)
            counts[status] += 1
            if position < len(df) - 1:
                delay = random.randint(15, 25)
                print(f"Agle contact se pehle {delay} seconds ka intezaar...")
                time.sleep(delay)

        print(
            f"\nFinished: {counts['completed']} send actions complete, "
            f"{counts['failed']} failed/skipped, {counts['uncertain']} uncertain."
        )
        print("Composer clear hona delivery ka proof nahi; WhatsApp ticks check karein.")

    except FileNotFoundError:
        print(f"[ERROR] File nahi mili: {CONTACTS_FILE}")
    except KeyboardInterrupt:
        print("\nScript rok di gayi. Last chat ka result WhatsApp mein check karein.")
    except Exception as error:
        print(f"[ERROR] {type(error).__name__}: {error}")
        traceback.print_exc()
    finally:
        if driver is not None:
            try:
                input("Browser band karne ke liye Enter dabayein...")
            except (EOFError, KeyboardInterrupt):
                pass
            try:
                driver.quit()
            except Exception:
                pass

if __name__ == "__main__":
    main()
