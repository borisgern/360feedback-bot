---
id: TASK-2025-003
title: "Implement Respondent Flow for Taking a Survey"
status: done
priority: high
type: feature
estimate: 10h
assignee: "@AI-DocArchitect"
created: 2025-06-27
updated: 2025-06-27
parents: [TASK-2025-005]
children: []
arch_refs: [ARCH-bot-respondent-flow, ARCH-service-feedback-cycle]
audit_log:
  - {date: 2025-06-27, user: "@AI-DocArchitect", action: "created with status done"}
---
## Description
Implemented the user flow for a respondent to receive an invitation, complete, and submit a 360-feedback survey. This includes FSM for the survey, dynamic question presentation, and answer handling.

## Acceptance Criteria
- A user receives a Telegram message with an invitation to take a survey.
- Users who are not yet known to the bot receive their pending invitations upon first interaction (`/start`).
- Clicking "Start Survey" begins the FSM-based questionnaire.
- The bot sends questions one by one.
- For `scale` and `radio` questions, inline keyboards are presented for answers.
- For `textarea` questions, the bot accepts a free-text reply.
- After the last question, the bot saves all answers to the appropriate Google Sheet.
- The respondent's status is updated to `completed` in the cycle data.
- The user receives a thank you message upon completion.

## Definition of Done
- All FSM states and handlers for the survey are implemented in `bot/handlers/respondent.py`.
- The `_send_question` logic correctly displays different question types.
- Answer saving is functional and robust.
- Code is committed.
