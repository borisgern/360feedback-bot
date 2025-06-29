import logging

from datetime import date, datetime
from typing import Any, Dict, Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.exceptions import TelegramAPIError

from ..storage.models import Employee, FeedbackCycle, RespondentInfo
from ..config import settings
from ..storage.redis_storage import RedisStorageService
from .google_sheets import GoogleSheetsService
from .question_service import QuestionnaireService
from .employee_service import EmployeeService

logger = logging.getLogger(__name__)

class CycleService:
    def __init__(
        self,
        redis_service: RedisStorageService,
        google_sheets_service: GoogleSheetsService,
        questionnaire_service: QuestionnaireService,
    ):
        self._redis = redis_service
        self._g_sheets = google_sheets_service
        self._questionnaire = questionnaire_service

    async def get_active_cycles_count(self) -> int:
        """
        Returns the number of active feedback cycles.
        Note: This is a simplified implementation. A more robust solution would
        involve fetching each cycle and checking its status or using a dedicated
        set in Redis for active cycle IDs.
        """
        keys = await self._redis.get_keys_by_pattern("cycle:*")
        return len(keys)

    async def create_new_cycle(
        self, target_employee: Employee, respondent_ids: list[str], deadline: date
    ) -> FeedbackCycle:
        """Creates a new feedback cycle, stores it, and sets up the results sheet."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        cycle_id = f"{timestamp}_{target_employee.id}"

        respondents = {}
        for resp_id in respondent_ids:
            respondent_info = RespondentInfo(id=resp_id)
            respondents[resp_id] = respondent_info

        sheet_title = f"{timestamp}_{target_employee.full_name}"

        cycle = FeedbackCycle(
            id=cycle_id,
            sheet_title=sheet_title,
            target_employee_id=target_employee.id,
            respondents=respondents,
            deadline=deadline,
        )

        await self._redis.set_model(f"cycle:{cycle.id}", cycle)
        questions = await self._questionnaire.get_questionnaire()
        if not questions:
            # This can happen if the Questions sheet is empty or validation fails.
            raise ValueError("Could not retrieve questionnaire to create cycle.")
        headers = ["cycle_id", "respondent_id", "submitted_at"] + [q.result_column for q in questions if q.result_column]
        await self._g_sheets.create_worksheet(sheet_title, headers)

        logger.info(f"Successfully created feedback cycle {cycle_id}")
        return cycle

    async def get_cycle_by_id(self, cycle_id: str) -> Optional[FeedbackCycle]:
        """Retrieves a feedback cycle by its ID."""
        logger.info(f"Retrieving cycle with id: {cycle_id}")
        cycle = await self._redis.get_model(f"cycle:{cycle_id}", FeedbackCycle)
        if not cycle:
            logger.warning(f"Cycle with id {cycle_id} not found in Redis.")
        return cycle

    async def get_all_cycles(self) -> list[FeedbackCycle]:
        """Returns all cycles stored in Redis."""
        keys = await self._redis.get_keys_by_pattern("cycle:*")
        cycles = []
        for key in keys:
            cycle = await self._redis.get_model(key, FeedbackCycle)
            if cycle:
                cycles.append(cycle)
        return cycles

    async def save_cycle(self, cycle: FeedbackCycle) -> None:
        """Persists the updated cycle back to Redis."""
        await self._redis.set_model(f"cycle:{cycle.id}", cycle)

    async def send_invitation(
        self,
        bot: Bot,
        cycle: FeedbackCycle,
        respondent: Employee,
        target_employee: Employee
    ):
        """Generates and sends a survey invitation message with a 'Start Survey' button."""
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        button_callback_data = f"start_survey:{cycle.id}:{respondent.id}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Начать опрос", callback_data=button_callback_data)]
        ])

        message_text = (
            f"Привет! 👋\n\n"
            f"Приглашаем тебя принять участие в опросе 360° для робота <b>{target_employee.full_name}</b>.\n"
            f"Твой фидбэк очень важен. Пожалуйста, пройди опрос до {cycle.deadline.strftime('%d.%m.%Y')}."
        )
        await bot.send_message(
            chat_id=respondent.telegram_id,
            text=message_text,
            reply_markup=keyboard
        )

    async def notify_respondents(
        self,
        cycle: FeedbackCycle,
        employee_service: EmployeeService,
        bot: Bot,
    ):
        logger.info(f"Starting notification process for cycle {cycle.id}.")
        target_employee = employee_service.find_by_id(cycle.target_employee_id)
        if not target_employee:
            logger.error(f"Cannot notify respondents for cycle {cycle.id}: Target employee not found.")
            return

        for resp_id in cycle.respondents:
            respondent = employee_service.find_by_id(resp_id)
            if respondent and respondent.telegram_id:
                logger.info(f"Found respondent {respondent.id} with telegram_id {respondent.telegram_id}. Attempting to send invitation.")
                try:
                    await self.send_invitation(bot, cycle, respondent, target_employee)
                    logger.info(f"Successfully sent invitation to {respondent.id}.")
                except TelegramAPIError as e:
                    logger.error(f"Failed to send invitation to {respondent.id} ({respondent.telegram_id}): {e}. Queuing notification.")
                    await self.add_pending_notification(respondent.id, cycle.id)
            elif respondent:
                logger.info(f"Respondent {respondent.id} does not have a telegram_id. Queuing notification.")
                await self.add_pending_notification(respondent.id, cycle.id)
            else:
                logger.warning(f"Respondent with ID {resp_id} not found. Skipping notification.")
        logger.info(f"Finished notification process for cycle {cycle.id}.")

    async def add_pending_notification(self, employee_id: str, cycle_id: str):
        """Adds a cycle ID to the set of pending notifications for an employee."""
        await self._redis.add_to_set(f"pending_notifications:{employee_id}", cycle_id)

    async def get_pending_notifications(self, employee_id: str) -> set[str]:
        """Retrieves the set of pending notification cycle IDs for an employee."""
        return await self._redis.get_set(f"pending_notifications:{employee_id}")

    async def clear_pending_notifications(self, employee_id: str):
        """Deletes the set of pending notifications for an employee."""
        await self._redis.delete_key(f"pending_notifications:{employee_id}")

    async def close_cycle(self, cycle_id: str) -> bool:
        """Closes an active cycle."""
        cycle = await self.get_cycle_by_id(cycle_id)
        if not cycle or cycle.status != "active":
            logger.warning(f"Attempted to close non-active or non-existent cycle {cycle_id}")
            return False

        cycle.status = "closed"
        await self._redis.set_model(f"cycle:{cycle.id}", cycle)
        logger.info(f"Cycle {cycle_id} has been closed.")
        # TODO: Trigger report generation in the future
        return True

    async def _notify_admin_on_progress(
        self,
        cycle: FeedbackCycle,
        completed_respondent: Employee,
        employee_service: EmployeeService,
        bot: Bot,
    ):
        """Sends a progress update to all admins when a respondent completes a survey."""
        target_employee = employee_service.find_by_id(cycle.target_employee_id)

        completed_count = sum(1 for r in cycle.respondents.values() if r.status == "completed")
        total_count = len(cycle.respondents)
        progress_percent = int((completed_count / total_count) * 100)

        remaining_respondents = [
            employee_service.find_by_id(r.id)
            for r in cycle.respondents.values()
            if r.status == "pending"
        ]
        remaining_nicks = [f"@{emp.id}" for emp in remaining_respondents if emp]

        message_text = (
            f"<b>Цикл: {target_employee.full_name}</b> (<code>{cycle.id}</code>)\n"
            f"Заполнил: {completed_respondent.full_name} ✅\n"
            f"Прогресс: {completed_count} / {total_count} ({progress_percent}%)\n\n"
        )
        if remaining_nicks:
            message_text += f"Осталось: {', '.join(remaining_nicks)}"
        else:
            message_text += "✨ Все респонденты заполнили анкеты!"

        # The button is now displayed if at least one respondent has completed the survey
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Завершить сейчас", callback_data=f"finish_cycle:{cycle.id}")]
        ])

        for admin_id in settings.ADMIN_TELEGRAM_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=message_text,
                    reply_markup=keyboard,
                )
            except TelegramAPIError as e:
                logger.error(f"Failed to send progress notification to admin {admin_id}: {e}")

    async def save_answers(
        self,
        cycle_id: str,
        respondent_id: str,
        answers: Dict[str, Any],
        employee_service: EmployeeService,
        bot: Bot,
    ) -> None:
        """Saves the respondent's answers to Google Sheets and updates the cycle status."""
        cycle = await self.get_cycle_by_id(cycle_id)
        if not cycle:
            logger.error(f"Cannot save answers: Cycle {cycle_id} not found.")
            return

        completed_respondent = employee_service.find_by_id(respondent_id)
        if not completed_respondent:
            # This is a critical error, should not happen if data is consistent
            logger.error(f"Could not find completed respondent with id {respondent_id} in EmployeeService.")
            # We proceed without notification, but the error is logged.

        target_employee = employee_service.find_by_id(cycle.target_employee_id)
        if not target_employee:
            logger.error(f"Cannot save answers: Target employee for cycle {cycle_id} not found.")
            return

        questions = await self._questionnaire.get_questionnaire()
        if not questions:
            logger.error(f"Cannot save answers: Questionnaire not found for cycle {cycle_id}.")
            return

        sheet_timestamp = cycle.created_at.strftime('%Y%m%d_%H%M%S')
        sheet_title = f"{sheet_timestamp}_{target_employee.full_name}"
        row_data = [cycle_id, respondent_id, datetime.now().isoformat()] + [answers.get(q.id) for q in questions]
        await self._g_sheets.append_row(sheet_title, row_data)

        cycle.respondents[respondent_id].status = "completed"
        cycle.respondents[respondent_id].completed_at = datetime.now()
        await self._redis.set_model(f"cycle:{cycle.id}", cycle)
        logger.info(f"Successfully saved answers for respondent {respondent_id} in cycle {cycle_id}.")
        
        if completed_respondent:
            await self._notify_admin_on_progress(cycle, completed_respondent, employee_service, bot)

