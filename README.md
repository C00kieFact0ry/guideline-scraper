## Guideline Scraper

Scrapes Dutch guideline websites.

### How to run
Run the ```main.py``` to start scraping.

### How to add a new source website
Add a new scraper in ```scrapers.py``` that inherits from ```BaseScraper```.
Then add it to the list of scrapers in ```main.py```.