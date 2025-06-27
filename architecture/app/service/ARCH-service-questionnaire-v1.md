---
id: ARCH-service-questionnaire
title: "Service: Questionnaire Management"
type: service
layer: application
owner: @team-backend
version: v1
status: current
created: 2025-06-27
updated: 2025-06-27
tags: [service, questionnaire, cache]
depends_on: [ARCH-data-source-gsheets, ARCH-data-source-redis]
referenced_by: []
---
## Context
The Questionnaire Service is responsible for providing the list of survey questions to be used in a feedback cycle. It abstracts the data source and adds a caching layer for performance.

## Structure
- **Service Class:** `backend/src/services/question_service.py::QuestionnaireService`
- **Data Models:** `backend/src/storage/models.py::Question`, `Questionnaire`
- **Primary Data Source:** `"Questions"` worksheet in Google Sheets.
- **Cache:** Redis is used to cache the entire questionnaire.
  - **Cache Key:** `questionnaire_v2`
  - **Cache TTL:** 3600 seconds (1 hour).

## Behavior
- **`get_questionnaire()`**: This is the primary method of the service.
  1. It first attempts to fetch the `Questionnaire` object from the Redis cache using `redis_service.get_model`.
  2. **Cache Hit:** If found, it returns the list of `Question` objects from the cached model.
  3. **Cache Miss:** If not found in the cache:
     a. It fetches all records from the `"Questions"` worksheet in Google Sheets.
     b. It processes each record:
        - Parses the `options` string (supports comma or semicolon delimiters) into a list of strings.
        - Coerces the `required` field into a boolean.
     c. It validates each processed record into a `Question` Pydantic model.
     d. It wraps the list of `Question`s in a `Questionnaire` model.
     e. It stores this `Questionnaire` object in Redis with a 1-hour TTL.
     f. It returns the list of `Question`s.

This caching strategy ensures that the bot doesn't need to query Google Sheets for the question list on every single survey start, significantly improving performance and resilience.

## Evolution
### Planned
- Could introduce versioning for questionnaires if they are expected to change significantly over time.

### Historical
- v1: Initial implementation with G-Sheets backend and Redis caching.
