---
id: TASK-2025-002
title: "Implement Admin Flow for Feedback Cycle Creation"
status: done
priority: high
type: feature
estimate: 12h
assignee: "@AI-DocArchitect"
created: 2025-06-27
updated: 2025-06-27
parents: [TASK-2025-004]
children: []
arch_refs: [ARCH-bot-admin-flow, ARCH-service-feedback-cycle]
audit_log:
  - {date: 2025-06-27, user: "@AI-DocArchitect", action: "created with status done"}
---
## Description
Implemented the end-to-end user flow for an administrator to create a new 360-feedback cycle. This includes command handling, a multi-step FSM, and dynamic keyboards for user selection.

## Acceptance Criteria
- An admin can start the flow with a `/new_cycle` command.
- The command is only accessible to users listed in `ADMIN_TELEGRAM_IDS`.
- The admin is guided to select one target employee from a paginated list.
- The admin can select multiple respondents from a paginated list, with options to select/deselect all.
- The admin is prompted to enter a deadline for the cycle.
- The bot validates that the deadline is a future date.
- A confirmation screen is shown with a summary of the cycle before final creation.
- Upon confirmation, a new `FeedbackCycle` is created, a results sheet is created in Google Sheets, and all respondents are notified.
- The admin can cancel the process at the final confirmation step.

## Definition of Done
- All FSM states and handlers are implemented in `bot/handlers/admin.py`.
- All required keyboards are implemented.
- The flow is fully functional from start to finish.
- Code is committed.
