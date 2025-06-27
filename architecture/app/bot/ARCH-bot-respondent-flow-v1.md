---
id: ARCH-bot-respondent-flow
title: "Bot Flow: Respondent Survey"
type: feature
layer: presentation
owner: @team-product
version: v1
status: current
created: 2025-06-27
updated: 2025-06-27
tags: [bot, respondent, fsm, survey]
depends_on: [ARCH-service-feedback-cycle, ARCH-service-questionnaire, ARCH-service-employee]
referenced_by: []
---
## Context
This document describes the flow for an employee (respondent) who is participating in a 360-feedback survey. This includes receiving the invitation, answering questions, and submitting the survey.

## Structure
- **Main Handler File:** `backend/src/bot/handlers/respondent.py`
- **FSM States:** Defined in `respondent.py`, class `SurveyStates`.
  - `in_survey`: The single state used while the respondent is actively answering questions.
- **Key Services:**
  - `CycleService`: To get cycle details and save answers.
  - `QuestionnaireService`: To get the list of questions.
  - `EmployeeService`: To identify the user and register their `telegram_id`.

## Behavior
1.  **Invitation:** A respondent receives a message from the bot inviting them to participate in a survey for a colleague. This message contains an "Начать опрос" (Start Survey) button. Invitations are sent by `CycleService` when a cycle is created.
2.  **Pending Notifications:** If a respondent was not registered with the bot (no `telegram_id`) when the cycle was created, the invitation is queued. When the user interacts with the bot for the first time (e.g., via `/start`), the system identifies them, registers their `telegram_id`, and delivers any pending invitations.
3.  **Starting the Survey:**
    - The respondent clicks the "Start Survey" button.
    - The `start_survey` callback handler is triggered.
    - The system fetches the questionnaire using `QuestionnaireService`.
    - The FSM is started, transitioning to the `SurveyStates.in_survey` state. Data like `cycle_id`, `questions`, and `current_question_index` is stored in the FSM context.
4.  **Answering Questions:**
    - A helper function `_send_question` is responsible for sending the current question to the user.
    - It formats the question text and dynamically creates an inline keyboard based on the question `type` (`scale`, `radio`). For `textarea` questions, no keyboard is sent, and a text response is expected.
    - The respondent answers by either clicking an inline button or sending a text message.
5.  **Processing Answers:**
    - Callbacks (`process_answer_cb`) and message handlers (`process_answer`) capture the response.
    - The answer is stored in the FSM context.
    - `current_question_index` is incremented.
    - `_send_question` is called again to send the next question.
6.  **Completing the Survey:**
    - When the last question is answered, the survey is complete.
    - The system calls `cycle_service.save_answers`.
    - This service appends the answers as a new row in the corresponding Google Sheet and updates the respondent's status to "completed" in the `FeedbackCycle` object in Redis.
    - A thank you message is sent to the respondent, and the FSM state is cleared.

## Evolution
### Planned
- Could add a feature to save draft answers and resume the survey later.

### Historical
- v1: Initial implementation of the survey-taking flow.
