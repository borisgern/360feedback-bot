import logging
from typing import Dict, List, Optional

from pydantic import ValidationError

from ..storage.models import Employee
from .google_sheets import GoogleSheetsService

logger = logging.getLogger(__name__)
EMPLOYEES_SHEET_NAME = "Employees"


class EmployeeService:
    """
    Service for fetching and managing employee data from Google Sheets.
    """

    def __init__(self, google_sheets_service: GoogleSheetsService):
        self._g_sheets = google_sheets_service
        self._employees: List[Employee] = []
        self._employee_map_by_id: Dict[str, Employee] = {}

    async def load_employees(self) -> None:
        """Loads or reloads the list of employees from the source."""
        logger.info("Loading employees from Google Sheets...")
        records = await self._g_sheets.get_all_records(EMPLOYEES_SHEET_NAME)
        if not records:
            logger.error("No employee records found in Google Sheets.")
            self._employees = []
            self._employee_map_by_id = {}
            return

        valid_employees = []
        for rec in records:
            try:
                valid_employees.append(Employee.model_validate(rec))
            except ValidationError as e:
                logger.warning(f"Skipping invalid employee record: {rec}. Error: {e}")

        self._employees = valid_employees
        self._employee_map_by_id = {emp.id: emp for emp in self._employees}
        logger.info(f"Successfully loaded {len(self._employees)} employees.")

    def find_by_id(self, employee_id: str) -> Optional[Employee]:
        """Finds an employee by their ID from the loaded list."""
        return self._employee_map_by_id.get(employee_id)
