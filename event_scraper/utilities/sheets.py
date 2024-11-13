import os.path
from typing import List, Optional, Any, Dict, Union
from seleniumbase import BaseCase
from seleniumbase import Driver
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, date, timedelta
from pathlib import Path
import re
import os
import string
from ..utilities.logger import project_logger


class MapsBusinessInfo:
    """A class to handle Google Sheets operations including creating, reading, and writing data.

    This class manages authentication with Google Sheets API and provides methods for
    spreadsheet manipulation including creating new sheets, reading/writing values,
    and formatting.
    """

    def __init__(self) -> None:
        """Initialize the MapsBusinessInfo with Google Sheets credentials."""
        self.logger = project_logger.get_logger(__name__)
        self.creds: Optional[Credentials] = None
        self.SCOPES: List[str] = ["https://www.googleapis.com/auth/spreadsheets"]
        self.create_tokens()
        self.logger.info("Successfully initialized Google Sheets service")

    def create_tokens(self) -> None:
        """Create or refresh Google API authentication tokens.

        Handles the OAuth2 flow to either create new tokens or refresh existing ones.
        Saves the credentials to token.json for future use.
        """
        self.logger.info("Starting token creation/refresh process")
        try:
            # Try to load existing tokens
            if os.path.exists("token.json"):
                try:
                    self.logger.debug("Found existing token.json")
                    self.creds = Credentials.from_authorized_user_file(
                        "token.json", self.SCOPES
                    )
                except Exception as token_error:
                    self.logger.warning(f"Error loading token.json: {token_error}")
                    self.creds = None
                    # Delete invalid token file
                    os.remove("token.json")

            # Create new tokens if needed
            if not self.creds or not self.creds.valid:
                self.logger.info("Tokens need refresh or creation")
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    try:
                        self.logger.info("Refreshing expired tokens")
                        self.creds.refresh(Request())
                    except Exception as refresh_error:
                        self.logger.warning(f"Token refresh failed: {refresh_error}")
                        self.creds = None

                # If still no valid credentials, create new ones
                if not self.creds:
                    self.logger.info("Creating new tokens through OAuth flow")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        "credentials.json", self.SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)

                # Save valid tokens
                self.logger.info("Saving tokens to token.json")
                with open("token.json", "w") as token:
                    token.write(self.creds.to_json())

            self.logger.info("Successfully initialized Google Sheets service")
        except Exception as e:
            self.logger.error(f"Failed to create/refresh tokens: {e}", exc_info=True)
            raise

    def create_new_spreadsheet(self, title: str) -> Optional[str]:
        """Create a new Google Spreadsheet.

        Args:
            title: The title for the new spreadsheet.

        Returns:
            The spreadsheet ID if successful, None if creation fails.
        """
        self.logger.info(f"Creating new spreadsheet with title: {title}")
        try:
            service = build("sheets", "v4", credentials=self.creds)
            spreadsheet: Dict[str, Any] = {"properties": {"title": title}}
            spreadsheet = (
                service.spreadsheets()
                .create(body=spreadsheet, fields="spreadsheetId")
                .execute()
            )
            self.spreadsheet_id = spreadsheet.get("spreadsheetId")
            self.logger.info(
                f"New spreadsheet created with spreadsheet ID {self.spreadsheet_id}"
            )
            return self.spreadsheet_id
        except Exception as e:
            self.logger.error(f"Failed to create spreadsheet: {e}", exc_info=True)
            return None

    def create_new_sheet(self, spreadsheet_id: str, sheet_title: str) -> Optional[int]:
        """Create a new sheet within an existing spreadsheet.

        Args:
            spreadsheet_id: The ID of the target spreadsheet.
            sheet_title: The title for the new sheet.

        Returns:
            The sheet ID (gid) if successful, None if creation fails.
        """
        self.logger.info(
            f"Creating new sheet '{sheet_title}' in spreadsheet {spreadsheet_id}"
        )
        try:
            service = build("sheets", "v4", credentials=self.creds)
            spreadsheet = (
                service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            )
            existing_sheets = spreadsheet.get("sheets", [])
            existing_titles = [
                sheet["properties"]["title"] for sheet in existing_sheets
            ]
            if sheet_title in existing_titles:
                sheet = next(
                    sheet
                    for sheet in existing_sheets
                    if sheet["properties"]["title"] == sheet_title
                )
                sheet_gid = sheet["properties"]["sheetId"]
                print(f"Sheet '{sheet_title}' already exists. Returning its sheet ID.")
                return sheet_gid

            request = {"addSheet": {"properties": {"title": sheet_title}}}
            response = (
                service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": [request]})
                .execute()
            )
            sheet_gid = response["replies"][0]["addSheet"]["properties"]["sheetId"]
            self.logger.info(f"Successfully created sheet with ID: {sheet_gid}")
            return sheet_gid
        except Exception as e:
            self.logger.error(f"Failed to create new sheet: {e}", exc_info=True)
            return None

    def read_values(
        self,
        spreadsheet_id: str,
        sheet_title: str = "Sheet1",
        range: Optional[str] = None,
    ) -> List[List[Any]]:
        """Read values from a specified range in a spreadsheet for a specific Sheet.

        Args:
            spreadsheet_id: The ID of the target spreadsheet.
            sheet_title: The title of the sheet to read from.
            range: Optional A1 notation range to read. If None, reads entire sheet.

        Returns:
            A 2D list containing the cell values.

        Raises:
            Exception: If reading fails.
        """
        self.logger.info(
            f"Reading values from spreadsheet {spreadsheet_id} for sheet with title {sheet_title}"
        )
        try:
            service = build("sheets", "v4", credentials=self.creds)
            sheet = service.spreadsheets()

            if range is None:
                self.logger.info(f"Reading entire sheet as range is None")
                sheet_metadata = sheet.get(spreadsheetId=spreadsheet_id).execute()
                sheet_info = next(
                    s
                    for s in sheet_metadata["sheets"]
                    if s["properties"]["title"] == sheet_title
                )
                sheet_id = sheet_info["properties"]["sheetId"]

                grid_properties = sheet_info["properties"]["gridProperties"]
                row_count = grid_properties["rowCount"]
                column_count = grid_properties["columnCount"]

                range = f"{sheet_title}!A1:{string.ascii_uppercase[column_count-1]}{row_count}"

            self.logger.info(f"range to read values {range}")
            result = (
                sheet.values().get(spreadsheetId=spreadsheet_id, range=range).execute()
            )
            self.logger.info(f"Successfully read {len(result)} rows of data")
            return result.get("values", [])
        except Exception as e:
            self.logger.error(f"Error reading values: {e}", exc_info=True)
            raise e

    def write_values(
        self,
        headers: List[str],
        data_lst: List[Any],
        spreadsheet_id: str,
        sheet_title: str = "Sheet1",
    ) -> None:
        """Write values to a spreadsheet, including headers if needed.

        Args:
            headers: List of column headers.
            data_lst: List of values to write.
            spreadsheet_id: The ID of the target spreadsheet.
            sheet_title: The title of the sheet to write to.

        Raises:
            Exception: If writing fails.
        """
        self.logger.info(
            f"Writing values to sheet '{sheet_title}' in spreadsheet {spreadsheet_id}"
        )
        try:
            service = build("sheets", "v4", credentials=self.creds)
            spreadsheet = (
                service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            )
            sheet = next(
                sheet
                for sheet in spreadsheet["sheets"]
                if sheet["properties"]["title"] == sheet_title
            )
            header_len = len(headers)
            len_as_str = string.ascii_uppercase[header_len - 1]
            sheet_range = f"{sheet_title}!A:{len_as_str}"

            sheet = service.spreadsheets()
            result = (
                sheet.values()
                .get(spreadsheetId=spreadsheet_id, range=sheet_range)
                .execute()
            )

            rows = result.get("values", [])
            self.logger.info(f"Total rows is {len(rows)}")

            ind = len(rows) + 1
            if not rows:
                upload_data_body = {
                    "valueInputOption": "RAW",
                    "data": [
                        {
                            "range": f"{sheet_title}!A{1}:{len_as_str}{1}",
                            "values": [headers],
                        }
                    ],
                }

                values_service = service.spreadsheets().values()
                values_service.batchUpdate(
                    spreadsheetId=spreadsheet_id, body=upload_data_body
                ).execute()
                ind += 1
            self.logger.info(f"headers is {headers}")
            self.logger.info(f"Data to be written is {data_lst}")

            upload_data_body = {
                "valueInputOption": "RAW",
                "data": [
                    {
                        "range": f"{sheet_title}!A{ind}:{len_as_str}{ind}",
                        "values": [data_lst],
                    }
                ],
            }

            sheet.values().batchUpdate(
                spreadsheetId=spreadsheet_id, body=upload_data_body
            ).execute()
            self.logger.info(
                f"Values written to {sheet_title} in spreadsheet {spreadsheet_id}"
            )
        except Exception as e:
            self.logger.error(f"Writing values to sheet error: {e}", exc_info=True)
            raise e

    def read_column_values(
        self, header_name: str, spreadsheet_id: str, sheet_title: str
    ) -> List[str]:
        """Read all values from a specific column identified by its header.

        Args:
            header_name: The name of the column header.
            spreadsheet_id: The ID of the target spreadsheet.
            sheet_title: The title of the sheet to read from.

        Returns:
            List of values from the specified column (excluding header).

        Raises:
            ValueError: If header_name is not found.
            Exception: If reading fails.
        """
        self.logger.info(
            f"Reading column values of sheet '{sheet_title}' in spreadsheet {spreadsheet_id}"
        )
        try:
            service = build("sheets", "v4", credentials=self.creds)
            spreadsheet = (
                service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            )

            header_range = f"{sheet_title}!1:1"
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=header_range)
                .execute()
            )
            headers = result.get("values", [])[0]

            if header_name not in headers:
                raise ValueError(f"Column header name - {header_name} not found")

            col_index = headers.index(header_name) + 1
            col_letter = string.ascii_uppercase[col_index - 1]

            column_range = f"{sheet_title}!{col_letter}:{col_letter}"
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=column_range)
                .execute()
            )
            rows = result.get("values", [])

            return [row[0] for row in rows[1:] if row]
        except ValueError as val_err:
            self.logger.error(val_err, exc_info=True)
            raise val_err
        except Exception as e:
            self.logger.error(
                f"Error reading column value for {header_name}: {e}", exc_info=True
            )
            raise e

    def write_column_values(
        self, header_name: str, values: List[Any], spreadsheet_id: str, sheet_title: str
    ) -> Dict[str, Any]:
        """Write values to a specific column identified by its header.

        Args:
            header_name: The name of the column header.
            values: List of values to write to the column.
            spreadsheet_id: The ID of the target spreadsheet.
            sheet_title: The title of the sheet to write to.

        Returns:
            Response from the Google Sheets API.

        Raises:
            ValueError: If header_name is not found.
            Exception: If writing fails.
        """
        self.logger.info(
            f"Writing column values of sheet '{sheet_title}' in spreadsheet {spreadsheet_id}"
        )
        try:
            service = build("sheets", "v4", credentials=self.creds)

            header_range = f"{sheet_title}!1:1"
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=header_range)
                .execute()
            )
            headers = result.get("values", [])[0]

            if header_name not in headers:
                raise ValueError(
                    f"Header '{header_name}' not found in sheet '{sheet_title}'"
                )

            col_index = headers.index(header_name) + 1
            col_letter = string.ascii_uppercase[col_index - 1]

            column_range = f"{sheet_title}!{col_letter}2:{col_letter}{len(values) + 1}"

            data = {"range": column_range, "values": [[value] for value in values]}

            return (
                service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=column_range,
                    valueInputOption="RAW",
                    body=data,
                )
                .execute()
            )
        except ValueError as val_err:
            self.logger.error(val_err, exc_info=True)
            raise val_err
        except Exception as e:
            self.logger.error(f"Error writing column values: {e}", exc_info=True)
            raise e

    def increase_rows(
        self, spreadsheet_id: str, sheet_title: str = "Sheet1", row_count: int = 10000
    ) -> None:
        """Increase the number of rows in a sheet.

        Args:
            spreadsheet_id: The ID of the target spreadsheet.
            sheet_title: The title of the sheet to modify.
            row_count: The new number of rows desired.

        Returns:
            Response from the API if successful, None if failed.
        """
        self.logger.info(
            f"Increasing rows in sheet '{sheet_title}' of spreadsheet {spreadsheet_id}"
        )
        try:
            service = build("sheets", "v4", credentials=self.creds)

            spreadsheet = (
                service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            )
            sheet_id = None
            for sheet in spreadsheet.get("sheets", []):
                if sheet.get("properties", {}).get("title") == sheet_title:
                    sheet_id = sheet.get("properties", {}).get("sheetId")
                    break

            if sheet_id is None:
                print(f"Sheet with title '{sheet_title}' not found.")
                return None

            requests = [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {"rowCount": row_count},
                        },
                        "fields": "gridProperties.rowCount",
                    }
                }
            ]
            body = {"requests": requests}

            response = (
                service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )
            self.logger.info(f"Successfully increased rows")
        except Exception as e:
            self.logger.error(f"Error increasing rows: {e}", exc_info=True)
            return None

    def write_headers(
        self, headers: List[str], spreadsheet_id: str, sheet_title: str = "Sheet1"
    ) -> Dict[str, Any]:
        """Write headers to the first row of a sheet.

        Args:
            headers: List of header names to write.
            spreadsheet_id: The ID of the target spreadsheet.
            sheet_title: The title of the sheet to write to.

        Returns:
            Response from the Google Sheets API.

        Raises:
            Exception: If writing fails.
        """
        self.logger.info(
            f"Writing headers in sheet '{sheet_title}' of spreadsheet {spreadsheet_id}"
        )
        try:
            service = build("sheets", "v4", credentials=self.creds)

            header_len = len(headers)
            len_as_str = string.ascii_uppercase[header_len - 1]
            header_range = f"{sheet_title}!A1:{len_as_str}1"

            data = {"range": header_range, "values": [headers]}
            self.logger.info(f"header range- {header_range}")

            response = (
                service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=header_range,
                    valueInputOption="RAW",
                    body=data,
                )
                .execute()
            )
            self.logger.info(f"Headers successfully written to sheet")
            return response

        except Exception as e:
            self.logger.error(f"Error writing headers: {e}", exc_info=True)
            raise e
