# Google Maps Business Scraper

A Python-based Google Maps scraper that automatically collects business information including names, addresses, social media links, websites, phone numbers, and reviews. Data is directly exported to Google Sheets.
## Setup & Installation
1. Clone the repository
2. Install dependencies: `poetry install`
3. Add Google Cloud `credentials.json` to `event_scraper/tests`
4. Configure `config.json` with spreadsheet ID, business types, locations and headers
5. Activate Virtual environment using `pyproject.toml` by using command `poetry shell`
6. Go to `event_scraper/tests` and run: `pytest test_scraper.py`

## Prerequisites
- Python 3.11
- Poetry ( added to environment variables or use py -m poetry )
- Google Cloud Project with Sheets API enabled
- Google Cloud credentials
