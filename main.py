from playwright.sync_api import sync_playwright
from scrapers import RichtlijnenDatabaseScraper
def main():

    scraper_dicts = [{'class':RichtlijnenDatabaseScraper, 'name':'richtlijnenDatabase', 'download_dir':None}]

    with sync_playwright() as playwright:
        for scraper in scraper_dicts:
            scraper_inst = scraper['class'](name=scraper['name'],
                                            playwright=playwright,
                                            download_dir=scraper['download_dir'])
            scraper_inst.run()


if __name__ == "__main__":
    main()