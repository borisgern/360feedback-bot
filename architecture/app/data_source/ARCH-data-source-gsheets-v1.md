---
id: ARCH-data-source-gsheets
title: "Data Source: Google Sheets"
type: component
layer: infrastructure
owner: @team-backend
version: v1
status: current
created: 2025-06-27
updated: 2025-06-27
tags: [g-sheets, data-source, infrastructure]
depends_on: []
referenced_by: []
---
## Context
Google Sheets serves as the primary, human-editable data store for foundational information: the list of company employees and the master list of survey questions. It is also the destination for storing raw feedback data collected from surveys.

## Structure
- **Service Class:** `backend/src/services/google_sheets.py::GoogleSheetsService`
- **Library:** `gspread` is used to interact with the Google Sheets API.
- **Authentication:** Uses a service account key file, the path to which is configured via environment variables.
- **Configuration:** The ID of the main spreadsheet is also configured via an environment variable (`GOOGLE_SHEET_ID`).

Key worksheets used:
- `"Employees"`: Contains the list of all employees. `EmployeeService` reads from here.
- `"Questions"`: Contains the master list of all possible survey questions. `QuestionnaireService` reads from here.
- **Dynamic Worksheets:** For each feedback cycle, a new worksheet is created (e.g., `"2025-06-27_John Doe"`) to store the collected answers. `CycleService` manages this.

## Behavior
The `GoogleSheetsService` provides an asynchronous interface over the synchronous `gspread` library by running its calls in a thread pool (`asyncio.to_thread`).

- **Retry Logic:** Implements a `tenacity` retry strategy (`@retry_strategy`) for key API calls to handle transient network issues or Google API rate limiting.
- **`get_all_records(sheet_name)`**: Fetches all rows from a worksheet and returns them as a list of dictionaries.
- **`create_worksheet(title, headers)`**: Creates a new worksheet within the spreadsheet and populates the first row with the provided headers. It handles cases where a worksheet with the same title already exists.
- **`append_row(worksheet_title, row_data)`**: Appends a new row of data to the end of a specified worksheet. This is used to save survey answers.

## Evolution
### Planned
- No major changes planned. The service is a stable, low-level component.

### Historical
- v1: Initial implementation providing core read/write capabilities with retry logic.
