---
id: TASK-2025-005
title: "Implement Questionnaire Management with Caching"
status: done
priority: medium
type: feature
estimate: 4h
assignee: "@AI-DocArchitect"
created: 2025-06-27
updated: 2025-06-27
parents: [TASK-2025-001]
children: [TASK-2025-003]
arch_refs: [ARCH-service-questionnaire, ARCH-data-model]
audit_log:
  - {date: 2025-06-27, user: "@AI-DocArchitect", action: "created with status done"}
---
## Description
Created the `QuestionnaireService` to handle fetching and parsing the survey questions. A Redis-based caching layer was implemented to improve performance and reduce reliance on the Google Sheets API.

## Acceptance Criteria
- `QuestionnaireService` can fetch and parse questions from the "Questions" Google Sheet.
- The service correctly parses the `options` string field into a list of strings.
- The fetched questionnaire is cached in Redis with a 1-hour TTL.
- Subsequent requests for the questionnaire within the TTL period are served from the cache.
- If the cache expires or is empty, the service falls back to fetching from Google Sheets.

## Definition of Done
- `QuestionnaireService` is fully implemented.
- Caching logic is working correctly.
- The respondent flow uses this service to get questions.
- Code is committed.
