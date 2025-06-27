---
id: ARCH-service-feedback-cycle
title: "Service: Feedback Cycle Management"
type: service
layer: application
owner: @team-backend
version: v1
status: current
created: 2025-06-27
updated: 2025-06-27
tags: [service, core-logic, feedback-cycle]
depends_on: [ARCH-data-source-gsheets, ARCH-data-source-redis, ARCH-service-employee, ARCH-service-questionnaire]
referenced_by: []
---
## Context
The Cycle Service contains the core business logic for the entire 360-feedback process. It orchestrates interactions between data sources and other services to manage the lifecycle of a feedback cycle, from creation to answer submission.

## Structure
- **Service Class:** `backend/src/services/cycle_service.py::CycleService`
- **Data Model:** `backend/src/storage/models.py::FeedbackCycle`
- **Dependencies:** This is a high-level service that depends on almost all other services: `RedisStorageService`, `GoogleSheetsService`, `QuestionnaireService`, and `EmployeeService`.

## Behavior

### Cycle Creation
- **`create_new_cycle(target_employee, respondent_ids, deadline)`**:
  1. Generates a unique `cycle_id`.
  2. Creates a `FeedbackCycle` Pydantic model instance.
  3. Stores the new `FeedbackCycle` object in Redis.
  4. Fetches the questionnaire to get the result column headers.
  5. Creates a new worksheet in Google Sheets to store the results for this cycle. The sheet is named based on the creation date and target employee's name.

### Respondent Notification
- **`notify_respondents(cycle, employee_service, bot)`**:
  1. Iterates through the list of respondents in the cycle.
  2. For each respondent, it attempts to find their `telegram_id` via `EmployeeService`.
  3. If a `telegram_id` exists, it calls `send_invitation` to send a direct message with a "Start Survey" button.
  4. If the message fails (e.g., user blocked the bot) or if the `telegram_id` is not yet known, it queues a notification by adding the `cycle_id` to a Redis set (`pending_notifications:{employee_id}`). These pending notifications are delivered when the user next interacts with the bot.

### Answer Management
- **`save_answers(cycle_id, respondent_id, answers, employee_service)`**:
  1. Retrieves the `FeedbackCycle` from Redis.
  2. Retrieves the questionnaire to ensure the correct order of answers.
  3. Formats the answers into a list to be written as a row.
  4. Appends the answer row to the cycle's specific Google Sheet using `GoogleSheetsService`.
  5. Updates the respondent's status to `"completed"` in the `FeedbackCycle` object.
  6. Saves the updated `FeedbackCycle` object back to Redis.

## Evolution
### Planned
- Add logic for closing cycles after the deadline.
- Implement functionality for generating reports from the collected data in Google Sheets.

### Historical
- v1: Initial implementation covering creation, notification, and answer saving.
