import random
import time
from abc import abstractmethod, ABC
from pathlib import Path

from playwright.sync_api import Playwright

from definitions import ROOT_DIR


class BaseScraper(ABC):
    """
    An abstract base class for a scraper.
    It handles the boilerplate setup and cleanup.
    """
    def __init__(self, playwright: Playwright, name: str, download_dir: Path | None = None):
        self.playwright = playwright
        self.name = name

        # Will be created in run method
        self.browser = None
        self.context = None
        self.page = None

        self._download_dir = download_dir

    def run(self):
        """
        Public method to start the scraper.
        This handles the setup and cleanup.
        """
        try:
            print(f"Starting Scraper: {self.name}")
            # Each scraper gets its own fresh browser
            self.browser = self.playwright.chromium.launch(headless=True)
            self.context = self.browser.new_context(accept_downloads=True)
            self.page = self.context.new_page()

            # Create the download directory
            self.download_dir.mkdir(exist_ok=True)

            #Go to the base URL
            self.page.goto(str(self.base_URL))

            # Call the site-specific scraping logic
            self.scrape()

        except Exception as e:
            print(f"Failed to run {self.name}.")
            raise Exception(e)
        finally:
            # Ensure we always clean up
            if self.browser:
                self.browser.close()
            print(f"Finished scraping: {self.name}")

    @abstractmethod
    def scrape(self):
        """
        This is the main method that subclasses must implement.
        All site-specific scraping logic goes here.
        """
        pass

    @property
    @abstractmethod
    def base_URL(self) -> Path:
        """base URL of the site to scrape"""
        raise NotImplementedError

    @property
    def download_dir(self) -> Path:
        """
        The default download directory.
        Child classes can override this property for custom paths.
        """
        if self._download_dir is None:
            return Path(ROOT_DIR) / 'downloads' / self.name
        else:
            return self._download_dir

class RichtlijnenDatabaseScraper(BaseScraper):
    """
    Scrapes PDF guidelines from richtlijnendatabase.nl.
    """

    # Class constant for the relative link prefix
    LINK_PREFIX = "/richtlijn/"

    def __init__(self, playwright: Playwright, name:str, download_dir: Path | None = None):
        # Pass the required info to the BaseScraper's init
        super().__init__(playwright, name=name, download_dir=download_dir)

    @property
    def base_URL(self) -> Path:
        return Path("https://richtlijnendatabase.nl")

    def scrape(self):
        """
        Implement the site-specific scraping logic.
        The BaseScraper's .run() method will call this.
        """

        # Get rid of the cookie banner
        try:
            # Use the ID selector for the link you found
            cookie_button = self.page.locator("#cookie-notice-accept")

            # Click it (give it a 5-sec timeout, just in case)
            cookie_button.click(timeout=5000)
            print("  Clicked cookie banner 'Ik ga akkoord'.")

        except Exception as e:
            # If it fails, it's probably because the banner wasn't there.
            print(f"  Cookie banner not found or already gone.")
            pass

        # Find all <a> tags whose href starts with the prefix
        link_locators = self.page.locator(f'a[href^="{self.LINK_PREFIX}"]')

        # It's unclear when this page is ready to be scraped.
        # We assume it is ready when network is idle.
        print("Waiting for page network to be idle...")
        self.page.wait_for_load_state('networkidle', timeout=30000)
        print("Network is idle. Extracting hrefs...")

        # locator gives list of links, get the hrefs from them.
        all_hrefs = link_locators.evaluate_all(
            "list => list.map(element => element.href)"
        )

        # Filter for unique URLs
        unique_urls = sorted(list(set(all_hrefs)))

        print(f"Found {len(unique_urls)} unique richtlijn URLs.")

        # Retrieve files from URLs
        for i, url in enumerate(unique_urls):
            print(f"\x1b[94m\nProcessing {i + 1}/{len(unique_urls)}: {url}\x1b[0m")
            name = url.split("/")[-1]
            save_path = self.download_dir / f"{name}.pdf"

            # Don't re-download if file already exists
            if save_path.exists():
                print(f"  File already exists. Skipping.")
                continue

            # Go to the link
            self.page.goto(url, timeout=10000)

            # Click "Download richtlijn" button
            download_locator = self.page.get_by_role(
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
            popup_text = self.page.get_by_text(
                "Selecteer een van de volgende opties:",
                exact=True
            )

            # Wait for this text to become visible
            popup_text.wait_for(state="visible", timeout=10000)
            print("  Popup confirmed: Text 'Selecteer een...' is visible.")
            # Click "genereer" in the popup
            generate_button = self.page.get_by_role("button", name="GENEREER", exact=False)

            # Wait for the button to be visible
            generate_button.wait_for(state="visible", timeout=10000)
            print("  Found 'genereer' button.")

            # We must start 'expect_download' *before* the click
            with self.page.expect_download(timeout=5*60*1000) as download_info:
                generate_button.click()
                print("  Clicked 'genereer', waiting for download...")

            download = download_info.value

            # Save the file
            download.save_as(save_path)
            print(f"Successfully saved: {save_path.name}")

            # Add a small delay to be polite to the server
            time.sleep(random.randint(25, 50) / 100)

        # Note: No cleanup (browser.close) is needed here.
        # The BaseScraper's .run() method handles that in its 'finally' block.


class KennisinstituutVVNScraper(BaseScraper):
    """
    Scrapes PDF guidelines from richtlijnendatabase.nl.
    """

    # Class constant for the relative link prefix
    LINK_PREFIX = "https://kennisplatform.venvn.nl/onderwerp/"

    def __init__(self, playwright: Playwright, name:str, download_dir: Path | None = None):
        # Pass the required info to the BaseScraper's init
        super().__init__(playwright, name=name, download_dir=download_dir)

    @property
    def base_URL(self) -> Path:
        return Path("https://kennisplatform.venvn.nl/alle-onderwerpen/")

    def scrape(self):
        """
        Implement the site-specific scraping logic.
        The BaseScraper's .run() method will call this.
        """

        # Find all <a> tags whose href starts with the prefix
        link_locators = self.page.locator(f'a[href^="{self.LINK_PREFIX}"]')

        # Wait for the last link to appear before attempting to evaluate all links
        link_locators.last.wait_for(timeout=10000)

        # locator gives list of links, get the hrefs from them.
        all_hrefs = link_locators.evaluate_all(
            "list => list.map(element => element.href)"
        )

        # Filter for unique URLs
        unique_urls = sorted(list(set(all_hrefs)))

        print(f"Found {len(unique_urls)} unique richtlijn URLs.")

        # Retrieve files from URLs
        for i, url in enumerate(unique_urls):
            print(f"\x1b[94m\nProcessing {i + 1}/{len(unique_urls)}: {url}\x1b[0m")
            name = url.split("/")[-2]
            save_path = self.download_dir / f"{name}.pdf"

            # Don't re-download if file already exists
            if save_path.exists():
                print(f"  File already exists. Skipping.")
                continue

            self.page.goto(url, timeout=10000)

            # Click button that redirects to the PDF. Sometimes the text contains handreiking instead of richtlijn.
            download_locator = self.page.get_by_role(
                "link", name="Naar de richtlijn"
            ).or_(self.page.get_by_role(
                "link", name="Naar de handreiking"))

            if download_locator.count() == 0:
                print(f"No button found. Skipping.")
                continue
            if download_locator.count() > 1:
                raise Exception(f"Unexpected case: Multiple buttons found.")

            # We need to dip our toe in the water to check whether the button leads to a pdf
            href = download_locator.get_attribute("href")
            if href and href.endswith(".pdf"):
                print(f"Found direct PDF link: {href}. Attempting download...")
                # We must start 'expect_download' *before* the click
                with self.page.expect_download(timeout=5*60*1000) as download_info:
                    download_locator.click()
                    print("  Clicked button, waiting for download...")

                download = download_info.value

                # Save the file
                download.save_as(save_path)
                print(f"Successfully saved: {save_path.name}")
            else:
                print(f"Button is not a link or does not lead to PDF:{href}. Skipping.")



            # Add a small delay to be polite to the server
            time.sleep(random.randint(25, 50) / 100)

        # Note: No cleanup (browser.close) is needed here.
        # The BaseScraper's .run() method handles that in its 'finally' block.