from seleniumbase import BaseCase
from seleniumbase import Driver
from typing import List, Tuple, Optional, Any, Dict
from pathlib import Path
from ..utilities.xpath import *
from ..utilities.sheets import MapsBusinessInfo
from ..utilities.logger import project_logger
import json
import time
from contextlib import contextmanager

logger = project_logger.get_logger(__name__)


class GoogleMaps(BaseCase):
    """Google Maps scraper class for extracting business information."""

    def setUp(self) -> None:
        """Initialize the scraper with required configurations."""
        if not hasattr(self, "headers"):
            logger.error("Headers not initialized before setUp")
            raise ValueError("Headers must be set before calling setUp")

        super().setUp()
        self.maximize_window()
        self.sheets_api = MapsBusinessInfo()
        self.create_required_dir()
        self.change_proxy()
        self.sheet_identifier = "Sheet1"

    @contextmanager
    def safe_operation(self, operation_name: str):
        """Context manager for handling operations safely.

        Args:
            operation_name: Name of the operation being performed
        """
        try:
            logger.info(f"Starting {operation_name}")
            yield
            logger.info(f"Completed {operation_name}")
        except Exception as e:
            logger.error(f"Error during {operation_name}: {e}")
            raise

    def change_proxy(self) -> None:
        """Change the proxy by creating a new driver instance."""
        with self.safe_operation("proxy change"):
            new_driver = Driver(uc=True)
            self.switch_to_driver(new_driver)

    def safe_execute(self, func: callable, *args, **kwargs) -> Optional[Any]:
        """Safely execute a function with error handling."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error executing {func.__name__}: {e}")
            return None

    def create_required_dir(self) -> None:
        """Create required directories for the session."""
        with self.safe_operation("directory creation"):
            self.session_dir = Path("session")
            self.session_dir.mkdir(parents=True, exist_ok=True)

    def get_category_location(self) -> Tuple[tuple, tuple]:
        """Get business categories and locations from configuration."""
        with self.safe_operation("category location retrieval"):
            with open("category.json", "r") as file:
                data = json.load(file)
            self.spreadsheet_category_id = data["id"]
            values = self.sheets_api.read_values(self.spreadsheet_category_id)[1:]
            return zip(*values)

    def gmaps_input(
        self, type_of_business: str, location: str, url_identifier: str
    ) -> None:
        """Search for businesses on Google Maps and collect URLs.

        Args:
            type_of_business: Category of business to search
            location: Geographic location to search in
            url_identifier: Identifier for storing URLs
        """
        with self.safe_operation(
            f"Google Maps search for {type_of_business} in {location}"
        ):
            self.open("https://www.google.com/maps")
            self.check_for_element_with_intervals(GMAPS_SEARCH_BAR)
            self.type(GMAPS_SEARCH_BAR, f"{type_of_business} in {location}\n")

            try:
                self.scroll_get_all_links()
            except Exception as e:
                logger.warning(f"Error during scrolling: {e}")

            all_result_urls = self.extract_place_urls()
            if not all_result_urls:
                self.refresh_page()
                raise Exception("No results found")

            url_location = self.session_dir / f"{url_identifier}_url.json"
            url_location.touch(exist_ok=True)
            self.save_urls_to_json(all_result_urls, url_location)

    def extract_place_urls(self) -> List[str]:
        """Extract Google Maps place URLs from search results."""
        all_result_ele = self.find_elements(RESULT_URLS)
        return [
            ele.get_attribute("href")
            for ele in all_result_ele
            if ele.get_attribute("href").startswith("https://www.google.com/maps/place")
        ]

    def get_details(self, sheet_title: str, business: str) -> None:
        """Extract details for all places in search results.

        Args:
            sheet_title: Title of the sheet to store results
            business: Business category being processed
        """
        self.current_business_type = business
        urls = self.load_place_urls(sheet_title)

        for index, gmaps_link in enumerate(urls):
            try:
                if (index + 1) % 10 == 0:
                    self.refresh_proxy_session()

                self.open(gmaps_link)
                self.wait(2)

                # Extract all place details
                place_name = (
                    self.safe_execute(self.get_text, PLACE_NAME, timeout=1) or "NA"
                )

                if place_name == "NA":
                    self.open(gmaps_link)
                    self.wait(15)
                    self.scroll_place_div(1)
                    self.wait(2)
                    place_name = (
                        self.safe_execute(self.get_text, PLACE_NAME, timeout=1) or "NA"
                    )

                # Extract other details
                place_type = self.safe_execute(self.get_text, PLACE_TYPE, timeout=1)
                place_address = self.safe_execute(
                    self.get_text, PLACE_ADDRESS, timeout=1
                )

                self.scroll_place_div(200)
                place_website = self.safe_execute(
                    self.get_text, PLACE_WEBSITE, timeout=1
                )
                place_phone = self.safe_execute(self.get_text, PLACE_PHONE, timeout=1)
                place_review_star = self.safe_execute(
                    self.get_text, PLACE_REVIEW_STAR, timeout=1
                )

                # Process review count
                place_review_count = (
                    self.safe_execute(
                        lambda: self.get_text(PLACE_REVIEW_PEOPLE_NUMBER, timeout=1)
                        .replace("(", "")
                        .replace(")", "")
                    )
                    or "NA"
                )

                if place_review_count == "NA" and place_review_star:
                    place_review_count = "1"

                plus_code = self.safe_execute(self.get_text, PLACE_PLUS_CODE, timeout=1)

                # Get social media links
                social_links = self.get_social_media_links()

                # Compile all data
                place_data = [
                    place_name,
                    place_address,
                    social_links["instagram"],
                    social_links["facebook"],
                    place_website,
                    plus_code,
                    gmaps_link,
                    social_links["other"],
                    place_phone,
                    self.current_business_type,
                    place_type,
                    place_review_star,
                    place_review_count,
                ]

                # Sanitize and write data
                sanitized_data = self.sanitize_place_data(place_data)
                self.write_place_data(sanitized_data, sheet_title)

            except Exception as e:
                logger.error(f"Error processing place {index}: {e}")

    def get_social_media_links(self) -> dict:
        """Extract social media links from the place details."""
        for _ in range(8):  # Scroll multiple times to load all elements
            self.scroll_place_div(800)
            self.wait(0.2)
        self.wait(1)  # Extra wait for elements to load fully

        try:
            # Switch to the iframe containing the elements
            self.switch_to_frame("//iframe")
            elements = self.find_elements(WEB_SEARCH_RESULTS)
            print("len", len(elements))

            instagram_link = ""
            facebook_link = ""
            other_links = []

            for element in elements:
                try:
                    element.click()  # Click the element
                    self.wait(1)  # Wait for the new tab to open

                    # Switch to the new tab (assuming it opens as the second tab)
                    self.switch_to_newest_window()
                    current_url = self.get_current_url()  # Get the URL from the new tab
                    if "instagram.com" in current_url:
                        instagram_link = current_url
                    elif "facebook.com" in current_url:
                        facebook_link = current_url
                    else:
                        other_links.append(current_url)

                    # Close the new tab and switch back to the original tab
                    self.driver.close()
                    self.switch_to_default_window()

                    # Re-enter the iframe for further processing
                    self.switch_to_frame("//iframe")

                except Exception as e:
                    print(f"Error while processing an element: {e}")
                    # Ensure we return to the original tab and context
                    self.switch_to_window(0)
                    self.switch_to_frame("//iframe")
                    continue

            return {
                "instagram": instagram_link,
                "facebook": facebook_link,
                "other": " ; ".join(other_links),
            }

        except Exception as e:
            print(f"Error extracting social media links: {e}")
            return {"instagram": "", "facebook": "", "other": ""}

    def sanitize_place_data(self, place_data: List[str]) -> List[str]:
        """Ensure all place data fields have valid values."""
        return ["NA" if item is None or item == "" else item for item in place_data]

    def refresh_proxy_session(self) -> None:
        """Refresh the proxy session and browser."""
        with self.safe_operation("proxy session refresh"):
            try:
                self.driver.quit()
                self.change_proxy()
                self.open("https://www.google.com/")
            except Exception as e:
                logger.error(f"Failed to refresh proxy session: {e}")

    def load_place_urls(self, sheet_title: str) -> List[str]:
        """Load place URLs from stored JSON file."""
        filename = self.session_dir / f"{sheet_title}_url.json"
        with open(filename, "r") as file:
            return json.load(file)["urls"]

    def write_place_data(self, place_data: List[str], sheet_title: str) -> None:
        """Write place data to Google Sheets."""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                self.sheets_api.write_values(
                    self.headers, place_data, self.spreadsheet_id, sheet_title
                )
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(
                        f"Failed to write data after {max_retries} attempts: {e}"
                    )
                else:
                    self.wait(1)

    def scroll_place_div(self, value: int) -> None:
        """Scroll the place details div by specified amount."""
        try:
            div_element = self.find_element(SCROLLING_EVERY_SEARCH)
            current_position = self.driver.execute_script(
                "return arguments[0].scrollTop;", div_element
            )
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[1];",
                div_element,
                current_position + value,
            )
            self.wait(0.5)
        except Exception as e:
            logger.debug(f"Scroll operation failed: {e}")

    def scroll_get_all_links(self) -> None:
        """Scroll through search results to load all places."""
        result_ind = 0
        for _ in range(200):
            try:
                elements = self.find_elements(RESULT_ONE_BY_ONE)
                cur_ele = elements[result_ind]
                self.driver.execute_script("arguments[0].scrollIntoView()", cur_ele)
                self.wait(1)
                result_ind += 2
            except Exception as e:
                logger.debug(f"Scroll iteration failed: {e}")
                self.wait(1)

    def save_urls_to_json(self, links: List[str], filename: Path) -> None:
        """Save collected URLs to JSON file."""
        with open(filename, "w") as file:
            json.dump({"urls": links}, file, indent=4)

    def check_for_element_with_intervals(
        self, locator: str, interval: int = 2, timeout: int = 30
    ) -> bool:
        """Check for element presence with retries."""
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            try:
                self.find_element(locator)
                return True
            except Exception:
                time.sleep(interval)
        return False

    def create_spreadsheet(self, title: str) -> str:
        """Create a new Google Spreadsheet."""
        return self.sheets_api.create_new_spreadsheet(title)

    def create_sheet(self, spreadsheet_id: str, title: str) -> str:
        """Create a new sheet in existing spreadsheet."""
        return self.sheets_api.create_new_sheet(spreadsheet_id, title)
