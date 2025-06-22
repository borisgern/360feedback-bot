import logging

from datetime import date, datetime
from typing import Optional
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from ..storage.models import Employee, FeedbackCycle, RespondentInfo
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
        cycle_id = f"{datetime.now().strftime('%Y%m%d')}_{target_employee.id}"

        respondents = {}
        for resp_id in respondent_ids:
            respondent_info = RespondentInfo(id=resp_id)
            respondents[resp_id] = respondent_info

        cycle = FeedbackCycle(
            id=cycle_id,
            target_employee_id=target_employee.id,
            respondents=respondents,
            deadline=deadline,
        )

        await self._redis.set_model(f"cycle:{cycle.id}", cycle)

        sheet_title = f"{datetime.now().strftime('%Y-%m-%d')}_{target_employee.full_name}"
        questions = await self._questionnaire.get_questionnaire()
        if not questions:
            # This can happen if the Questions sheet is empty or validation fails.
            raise ValueError("Could not retrieve questionnaire to create cycle.")
        headers = ["cycle_id", "respondent_id", "submitted_at"] + [
            q.id for q in questions
        ]
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
            f"Приглашаем тебя принять участие в опросе 360° для коллеги <b>{target_employee.full_name}</b>.\n"
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

