import random

from playwright.sync_api import sync_playwright, Playwright
from pathlib import Path
import time

# --- Configuration ---
BASE_URL = "https://richtlijnendatabase.nl/"
LINK_PREFIX = "/richtlijn/" # note that the links are relative!
DOWNLOAD_DIR = Path("downloads")


# ---------------------

def run_richtlijnendatabase(playwright: Playwright):
    """
    Main function to run the scraping logic using the SYNC API.
    """
    # Ensure the download directory exists
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    print(f"Saving files to: {DOWNLOAD_DIR.resolve()}")

    # Launch browser (headless=True runs in background)
    browser = playwright.chromium.launch(headless=True)

    # Create a new browser context that accepts downloads
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()

    # --- Step 1 & 2: Get all links ---
    print(f"Going to {BASE_URL}.")
    page.goto(BASE_URL)

    # Get rid of the cookie banner
    try:
        # Use the ID selector for the link you found
        cookie_button = page.locator("#cookie-notice-accept")

        # Click it (give it a 5-sec timeout, just in case)
        cookie_button.click(timeout=5000)
        print("  Clicked cookie banner 'Ik ga akkoord'.")

    except Exception as e:
        # If it fails, it's probably because the banner wasn't there.
        print(f"  Cookie banner not found or already gone.")
        pass

    # Find all <a> tags whose href starts with the prefix
    link_locators = page.locator(f'a[href^="{LINK_PREFIX}"]')

    # locator gives list of links, get the hrefs from them.
    all_hrefs = link_locators.evaluate_all(
        "list => list.map(element => element.href)"
    )

    # Filter for unique URLs
    unique_urls = sorted(list(set(all_hrefs)))

    print(f"Found {len(unique_urls)} unique richtlijn URLs.")

    # --- Step 3: Loop through each link ---

    # To run all, change 'unique_urls[:5]' to 'unique_urls'
    for i, url in enumerate(unique_urls):
        try:
            print(f"\x1b[94m\nProcessing {i + 1}/{len(unique_urls)}: {url}\x1b[0m")
            name = url.split("/")[-1]
            save_path = DOWNLOAD_DIR / f"{name}.pdf"

            # Don't re-download if file already exists
            if save_path.exists():
                print(f"  File already exists. Skipping.")
                continue

            # Step 3: Go to the link
            page.goto(url, timeout=10000)

            # Step 4: Click "Download richtlijn" button
            download_locator = page.get_by_role(
                "link", name=" Download richtlijn"
            )

            if download_locator.count() == 0:
                print(f"  No 'Download richtlijn' button found. Skipping.")
                continue
            if download_locator.count() > 1:
                raise Exception(f"  Unexpected case: Multiple 'Download richtlijn' buttons found.")
            download_locator.click()
            print("  Clicked 'Download richtlijn'.")

            # Make sure the popup is visible by checking for a specific text
            popup_text = page.get_by_text(
                "Selecteer een van de volgende opties:",
                exact=True
            )

            # Wait for this text to become visible (e.g., 10-second timeout)
            popup_text.wait_for(state="visible", timeout=10000)
            print("  Popup confirmed: Text 'Selecteer een...' is visible.")
            # Step 5: Click "genereer" in the popup
            generate_button = page.get_by_role("button", name="GENEREER", exact=False)

            # Wait for the button to be visible
            generate_button.wait_for(state="visible", timeout=10000)
            print("  Found 'genereer' button.")

            # Step 6: Handle the download
            # We must start 'expect_download' *before* the click
            with page.expect_download() as download_info:
                generate_button.click()
                print("  Clicked 'genereer', waiting for download...")

            download = download_info.value

            # Save the file
            download.save_as(save_path)
            print(f"  ✅ Successfully saved: {save_path.name}")

            # Add a small delay to be polite to the server
            time.sleep(random.randint(25, 50) / 100)

        except Exception as e:
            # Catch errors on a per-page basis so the script doesn't stop
            print(f" Failed to process {url}. Error: {e}")
            pass

    # --- Cleanup ---
    context.close()
    browser.close()
    print("\n--- All done! ---")

with sync_playwright() as playwright:
    run(playwright)