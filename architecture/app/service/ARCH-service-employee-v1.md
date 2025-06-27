---
id: ARCH-service-employee
title: "Service: Employee Management"
type: service
layer: application
owner: @team-backend
version: v1
status: current
created: 2025-06-27
updated: 2025-06-27
tags: [service, employee, user-management]
depends_on: [ARCH-data-source-gsheets, ARCH-data-source-redis]
referenced_by: []
---
## Context
The Employee Service is responsible for managing employee data. It acts as an abstraction layer over the data sources, providing a clean, in-memory representation of employees for other parts of the application.

## Structure
- **Service Class:** `backend/src/services/employee_service.py::EmployeeService`
- **Data Model:** `backend/src/storage/models.py::Employee`
- **Primary Data Source:** `"Employees"` worksheet in Google Sheets.
- **Cache/Secondary Storage:** Redis is used to persist the mapping between an employee's ID (their Telegram nickname) and their numeric Telegram ID.

### In-Memory State:
The service maintains several in-memory data structures for fast lookups after the initial load:
- `_employees`: A `List[Employee]` of all employees.
- `_employee_map_by_id`: A `Dict[str, Employee]` for O(1) lookup by employee ID.
- `_employee_map_by_telegram_id`: A `Dict[int, Employee]` for O(1) lookup by Telegram ID.

## Behavior
- **`load_employees()`**:
  - Fetches all records from the "Employees" Google Sheet.
  - Validates each record and creates an `Employee` Pydantic model.
  - For each employee, it checks Redis for a stored `telegram_id` and populates the model if found.
  - Populates the in-memory lists and dictionaries.
  - This method is called at application startup.

- **`find_by_id(employee_id)`**: Finds an employee by their ID (Telegram nickname) from the in-memory map.

- **`find_by_telegram_id(telegram_id)`**: Finds an employee by their numeric Telegram ID from the in-memory map.

- **`register_telegram_id(username, telegram_id)`**:
  - Called when a user interacts with the bot (e.g., `/start`).
  - Finds the employee by their `username` (which is their `id`).
  - If found, it stores the `telegram_id` in Redis (`employee_tg_id:{username}`) and updates the in-memory `Employee` object and lookup map.

## Evolution
### Planned
- A mechanism to periodically refresh the employee list without restarting the bot could be added if the employee roster changes frequently.

### Historical
- v1: Initial implementation with loading from Google Sheets and in-memory caching.
