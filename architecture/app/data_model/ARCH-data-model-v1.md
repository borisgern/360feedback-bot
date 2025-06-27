---
id: ARCH-data-model
title: "Core Data Models"
type: data_model
layer: domain
owner: @team-backend
version: v1
status: current
created: 2025-06-27
updated: 2025-06-27
tags: [pydantic, model, domain]
depends_on: []
referenced_by: []
---
## Context
This document defines the core data structures (entities) of the application. These models are implemented using Pydantic for data validation, serialization, and clear schema definition. They are primarily located in `backend/src/storage/models.py`.

## Structure

### `Question`
Represents a single question in the survey.
- `id` (str): Unique identifier (e.g., "C-1").
- `text` (str): The question text, may contain placeholders like `{Имя}`.
- `type` (str): Type of question (e.g., "scale", "radio", "textarea").
- `options` (Optional[List[str]]): List of choices for "radio" or "checkbox" types.
- `required` (bool): Whether the question must be answered.
- `result_column` (Optional[str]): The name of the column in the Google Sheet where the answer is stored.

### `Questionnaire`
A wrapper model that contains a list of `Question` objects. This is the structure that gets cached in Redis.
- `questions` (List[Question]): The full list of survey questions.

### `Employee`
Represents a company employee.
- `telegram_nickname` (str): The user's Telegram @username. Used as the primary business key.
- `last_name` (str): Last name.
- `first_name` (str): First name.
- `telegram_id` (Optional[int]): The user's numeric Telegram ID, populated upon interaction with the bot.
- `id` (property): Computed from `telegram_nickname`.
- `full_name` (property): Computed from first and last names.

### `RespondentInfo`
Stores the status of a single respondent within a feedback cycle.
- `id` (str): The employee ID of the respondent.
- `status` (Literal["pending", "completed"]): The current status.
- `completed_at` (Optional[datetime]): Timestamp of completion.

### `FeedbackCycle`
The central model representing a single 360-feedback process.
- `id` (str): Unique ID for the cycle.
- `target_employee_id` (str): The employee being reviewed.
- `respondents` (Dict[str, RespondentInfo]): A dictionary mapping respondent IDs to their `RespondentInfo`.
- `deadline` (date): The date by which the survey should be completed.
- `status` (Literal["active", "closed", "reported"]): The overall status of the cycle.
- `created_at` (datetime): Timestamp of creation.

## Behavior
These models are used throughout the application, particularly by services for data transfer and by `RedisStorageService` for serialization to/from JSON for storage in Redis. Pydantic's validation ensures data integrity when loading from external sources like Google Sheets or from Redis.

## Evolution
### Planned
- The models may be extended with more fields as new features are added.

### Historical
- v1: Initial set of models to support the core feedback cycle functionality.
