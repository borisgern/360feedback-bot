import asyncio
import logging
from typing import Any, Dict, List

import gspread
from gspread.exceptions import APIError, WorksheetNotFound
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings

logger = logging.getLogger(__name__)

# Define a retry strategy for Google API calls to handle transient errors
retry_strategy = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=lambda retry_state: isinstance(retry_state.outcome.exception(), APIError),
    before_sleep=lambda retry_state: logger.warning(
        f"Retrying Google Sheets API call due to {retry_state.outcome.exception()} "
        f"(attempt {retry_state.attempt_number})"
    ),
)

class GoogleSheetsService:
    """
    Service for interacting with Google Sheets API using gspread.
    Includes retry logic and runs synchronous gspread calls in a thread pool.
    """

    def __init__(self, config: settings.google):
        self._client = gspread.service_account(
            filename=config.SERVICE_ACCOUNT_KEY_PATH
        )
        self._spreadsheet = self._client.open_by_key(config.SHEET_ID)

    @retry_strategy
    def _get_all_records_sync(self, sheet_name: str) -> List[Dict[str, Any]]:
        """Synchronously fetches all records from a worksheet."""
        try:
            worksheet = self._spreadsheet.worksheet(sheet_name)
            return worksheet.get_all_records()
        except WorksheetNotFound:
            logger.error(f"Worksheet '{sheet_name}' not found.")
            return []
        except APIError as e:
            logger.error(f"Google API error while fetching from '{sheet_name}': {e}")
            raise

    async def get_all_records(self, sheet_name: str) -> List[Dict[str, Any]]:
        """Asynchronously fetches all records from a specified worksheet."""
        return await asyncio.to_thread(self._get_all_records_sync, sheet_name)

    def _get_worksheet(self, worksheet_name: str) -> gspread.Worksheet:
        """Synchronously gets a worksheet by its name."""
        try:
            return self._spreadsheet.worksheet(worksheet_name)
        except WorksheetNotFound:
            logger.error(f"Worksheet '{worksheet_name}' not found.")
            raise

    @retry_strategy
    def _create_worksheet_sync(
        self, title: str, headers: List[str]
    ) -> gspread.Worksheet:
        try:
            worksheet = self._spreadsheet.add_worksheet(
                title=title, rows=1, cols=len(headers)
            )
            worksheet.append_row(headers, value_input_option="USER_ENTERED")
            return worksheet
        except APIError as e:
            if "already exists" in str(e):
                logger.warning(f"Worksheet '{title}' already exists. Re-using it.")
                return self._spreadsheet.worksheet(title)
            logger.error(f"Google API error while creating worksheet '{title}': {e}")
            raise

    async def create_worksheet(self, title: str, headers: List[str]) -> None:
        """Asynchronously creates a new worksheet with a header row."""
        await asyncio.to_thread(self._create_worksheet_sync, title, headers)

    @retry_strategy
    def _append_row_sync(self, worksheet_title: str, row_data: List[Any]) -> None:
        worksheet = self._spreadsheet.worksheet(worksheet_title)
        worksheet.append_row(row_data, value_input_option="USER_ENTERED")

    async def append_row(self, worksheet_title: str, row_data: List[Any]) -> None:
        """Asynchronously appends a row of data to the specified worksheet."""
        await asyncio.to_thread(self._append_row_sync, worksheet_title, row_data)
