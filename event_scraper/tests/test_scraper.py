import pytest
import json
from typing import Dict, List, Any
from ..pages.flyer_scraper import GoogleMaps
from ..utilities.logger import project_logger
from parameterized import parameterized
from contextlib import contextmanager

logger = project_logger.get_logger(__name__)


def load_config() -> Dict[str, Any]:
    """Load configuration from config.json file.

    Returns:
        Dict containing locations, business categories, spreadsheet_id, and headers
    """
    try:
        with open("config.json", "r") as file:
            logger.info("Loading configuration from config.json")
            return json.load(file)
    except FileNotFoundError:
        logger.error("config.json file not found")
        raise
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in config.json")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading config: {e}")
        raise


# Initialize the configuration
config = load_config()
locations = config["locations"]
business_categories = config["business_categories"]
spreadsheet_id = config["spreadsheet_id"]
headers = config["headers"]


class TestContact(GoogleMaps):
    """Test class for scraping contact information from Google Maps."""

    def setUp(self) -> None:
        """Initialize test setup with spreadsheet ID and headers."""
        try:
            # Initialize headers before calling parent setUp
            self.headers = headers
            super().setUp()
            self.spreadsheet_id = spreadsheet_id
            logger.info("Test setup completed successfully")
        except Exception as e:
            logger.error(f"Error during test setup: {e}")
            raise

    def teardown_method(self, method) -> None:
        """Clean up after test execution."""
        try:
            self.driver.quit()
            logger.info("Driver quit successfully")
        except Exception as e:
            logger.error(f"Failed to quit the driver: {e}")

    @contextmanager
    def safe_operation(self, operation_name: str = "operation"):
        """Context manager for safely executing operations with error handling.

        Args:
            operation_name: Name of the operation being performed
        """
        try:
            logger.info(f"Starting operation: {operation_name}")
            yield
            logger.info(f"Completed operation: {operation_name}")
        except Exception as e:
            logger.error(f"Error during {operation_name}: {e}")
            return None

    @parameterized.expand([(location,) for location in locations])
    def test_contact(self, location: str) -> None:
        """Test contact information scraping for a given location.

        Args:
            location: Geographic location to scrape
        """
        try:
            logger.info(f"Starting scraping for location: {location}")
            self.sheet_identifier = f"{location}"

            with self.safe_operation("create sheet"):
                self.sheet_gid = self.create_sheet(
                    self.spreadsheet_id, self.sheet_identifier
                )
                self.sheets_api.increase_rows(
                    self.spreadsheet_id, self.sheet_identifier
                )
                self.sheets_api.write_headers(
                    self.headers, self.spreadsheet_id, self.sheet_identifier
                )

            for business in business_categories:
                logger.info(f"Processing business category: {business}")
                with self.safe_operation(f"process business {business}"):
                    self.gmaps_input(business, location, self.sheet_identifier)
                    self.get_details(
                        sheet_title=self.sheet_identifier,
                        business=business,
                    )

                try:
                    self.driver.quit()
                    logger.info("Driver quit successfully after business processing")
                except Exception as e:
                    logger.warning(f"Failed to quit driver: {e}")

                with self.safe_operation("proxy change"):
                    self.change_proxy()
                    self.open("https://www.google.com/")

            logger.info(f"Completed scraping for location: {location}")
        except Exception as e:
            logger.error(f"Failed to process location {location}: {e}")
            raise
