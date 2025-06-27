import logging
from typing import Dict, List, Optional

from pydantic import ValidationError

from ..storage.models import Employee
from ..storage.redis_storage import RedisStorageService
from .google_sheets import GoogleSheetsService

logger = logging.getLogger(__name__)
EMPLOYEES_SHEET_NAME = "Employees"


class EmployeeService:
    """
    Service for fetching and managing employee data from Google Sheets.
    """

    def __init__(
        self,
        redis_service: RedisStorageService,
        google_sheets_service: GoogleSheetsService,
    ):
        self._redis = redis_service
        self._g_sheets = google_sheets_service
        self._employees: List[Employee] = []
        self._employee_map_by_id: Dict[str, Employee] = {}
        self._employee_map_by_telegram_id: Dict[int, Employee] = {}

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

        for emp in valid_employees:
            stored_tg_id = await self._redis.get(f"employee_tg_id:{emp.id}")
            if stored_tg_id:
                emp.telegram_id = int(stored_tg_id)

        self._employees = valid_employees
        self._employee_map_by_id = {emp.id: emp for emp in self._employees}
        self._employee_map_by_telegram_id = {
            emp.telegram_id: emp for emp in self._employees if emp.telegram_id
        }
        logger.info(f"Successfully loaded {len(self._employees)} employees.")
        logger.debug(f"Employee map by ID keys: {list(self._employee_map_by_id.keys())}")

    def find_by_id(self, employee_id: str) -> Optional[Employee]:
        """Finds an employee by their ID from the loaded list."""
        return self._employee_map_by_id.get(employee_id)

    def get_all_employees(self) -> List[Employee]:
        return self._employees

    async def register_telegram_id(self, username: str, telegram_id: int):
        """Saves a user's telegram_id and updates the in-memory mapping."""
        logger.info(f"Attempting to register telegram_id {telegram_id} for username '{username}'")
        employee = self.find_by_id(username)
        if employee:
            logger.info(f"Found employee {employee.id} for username '{username}'")
            if employee.telegram_id != telegram_id:
                employee.telegram_id = telegram_id
                self._employee_map_by_telegram_id[telegram_id] = employee
                await self._redis.set_value(f"employee_tg_id:{username}", str(telegram_id))
                logger.info(f"Registered telegram_id {telegram_id} for user @{username}.")
            else:
                logger.info(f"Telegram ID {telegram_id} is already registered for user @{username}.")
        else:
            logger.warning(f"Could not find employee with id '{username}' to register telegram_id.")

    def find_by_telegram_id(self, telegram_id: int) -> Optional[Employee]:
        """Finds an employee by their Telegram ID from the loaded list."""
        return self._employee_map_by_telegram_id.get(telegram_id)
