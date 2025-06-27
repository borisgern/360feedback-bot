---
id: ARCH-bot-admin-flow
title: "Bot Flow: Admin Cycle Creation"
type: feature
layer: presentation
owner: @team-product
version: v1
status: current
created: 2025-06-27
updated: 2025-06-27
tags: [bot, admin, fsm, cycle-creation]
depends_on: [ARCH-service-feedback-cycle, ARCH-service-employee]
referenced_by: []
---
## Context
This document describes the user flow for an administrator creating a new 360-feedback cycle. This is a primary administrative function of the bot, initiated by the `/new_cycle` command.

## Structure
The flow is implemented using `aiogram`'s Finite State Machine (FSM) to guide the admin through a multi-step process.

- **Main Handler File:** `backend/src/bot/handlers/admin.py`
- **FSM States:** Defined in `backend/src/bot/states/cycle_creation.py`, class `CycleCreationFSM`.
  - `waiting_for_target_employee`: Select the employee who is the subject of the feedback.
  - `waiting_for_respondents`: Select one or more employees who will provide feedback.
  - `waiting_for_deadline`: Set a deadline for the feedback cycle.
  - `confirming_creation`: Final confirmation before creating the cycle.
- **Keyboards:** Dynamically generated inline keyboards are used for selection.
  - `backend/src/bot/keyboards/employee_select_keyboard.py`: For selecting the target employee (paginated).
  - `backend/src/bot/keyboards/respondent_select_keyboard.py`: For selecting multiple respondents (paginated, with select/deselect all).
  - `backend/src/bot/keyboards/admin_keyboards.py`: For the final confirmation.
- **Middleware:** The entire `admin.py` router is protected by `AdminAuthMiddleware` to ensure only authorized admins can access these commands.

## Behavior
1.  An authorized admin sends the `/new_cycle` command.
2.  The bot checks if the maximum number of active cycles has been reached.
3.  The system loads the employee list using `EmployeeService`.
4.  The FSM transitions to `waiting_for_target_employee`. The bot presents a paginated list of employees to choose from.
5.  Admin selects a target employee. The state transitions to `waiting_for_respondents`.
6.  The bot presents a multi-select, paginated list of other employees to act as respondents. The admin can toggle selections, select all, or deselect all.
7.  Admin clicks "Done". The state transitions to `waiting_for_deadline`.
8.  The bot asks for a deadline in `YYYY-MM-DD` format.
9.  Admin provides a valid future date. The state transitions to `confirming_creation`.
10. The bot shows a summary of the new cycle (target, respondent count, deadline) and asks for confirmation.
11. Admin confirms. The `CycleService` is called to:
    - Create the `FeedbackCycle` object in Redis.
    - Create a new worksheet in Google Sheets for the results.
    - Notify all selected respondents via Telegram message.
12. The FSM state is cleared.

If the admin cancels at the confirmation step, the state is cleared and the process is aborted.

## Evolution
### Planned
- No immediate changes planned.

### Historical
- v1: Initial implementation of the cycle creation flow.
