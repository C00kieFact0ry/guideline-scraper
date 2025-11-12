from playwright.sync_api import sync_playwright
from scrapers import RichtlijnenDatabaseScraper
def main():

    scraper_dicts = [{'class':RichtlijnenDatabaseScraper, 'name':'richtlijnenDatabase'}]

    with sync_playwright() as playwright:
        for scraper in scraper_dicts:
            scraper_inst = scraper['class'](name=scraper['name'], playwright=playwright)
            scraper_inst.run()