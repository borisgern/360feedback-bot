import logging

from aiogram import F, Router, types, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from ...services.cycle_service import CycleService
from ...services.employee_service import EmployeeService

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, employee_service: EmployeeService, cycle_service: CycleService, bot: Bot):
    telegram_id = message.from_user.id
    logger.info(f"Received /start command from telegram_id: {telegram_id}")

    telegram_id = message.from_user.id
    username = message.from_user.username

    if username:
        await employee_service.register_telegram_id(username, telegram_id)

    employee = employee_service.find_by_telegram_id(telegram_id)

    if not employee:
        logger.warning(f"User with telegram_id {telegram_id} not found in employee list.")
        await message.answer("Привет! Я бот для сбора обратной связи 360°.\nК сожалению, я не нашел вас в списке сотрудников.")
        return

    logger.info(f"User found: {employee.id} ({employee.full_name}). Responding with greeting.")
    await message.answer(f"Привет, {employee.first_name}! 👋")

    # Check for pending notifications
    logger.info(f"Checking for pending notifications for employee {employee.id}.")
    pending_cycle_ids = await cycle_service.get_pending_notifications(employee.id)
    if not pending_cycle_ids:
        logger.info(f"No pending notifications for user {employee.id} ({telegram_id}).")
        return

    logger.info(f"Found {len(pending_cycle_ids)} pending notifications for user {employee.id}: {pending_cycle_ids}")
    for cycle_id in pending_cycle_ids:
        logger.info(f"Processing pending notification for cycle_id: {cycle_id}")
        cycle = await cycle_service.get_cycle_by_id(cycle_id)
        if not cycle:
            logger.warning(f"Could not find cycle with id {cycle_id}. Skipping.")
            continue

        target_employee = employee_service.find_by_id(cycle.target_employee_id)
        if cycle and target_employee:
            logger.info(f"Sending invitation for cycle {cycle.id} to respondent {employee.id} for target {target_employee.id}")
            await cycle_service.send_invitation(bot, cycle, employee, target_employee)
        else:
            logger.warning(f"Could not send pending notification for cycle {cycle_id} to user {employee.id}. Cycle or target not found.")

    await cycle_service.clear_pending_notifications(employee.id)
    logger.info(f"Cleared pending notifications for user {employee.id}.")


@router.callback_query(F.data.startswith("start_survey:"))
async def start_survey(callback: types.CallbackQuery, state: FSMContext):
    """
    Handles the 'Start Survey' button click.
    Starts the questionnaire FSM.
    """
    _, cycle_id, respondent_id = callback.data.split(":")

    # TODO: Implement Questionnaire FSM
    # 1. Check if survey is already completed
    # 2. Get questions from the service
    # 3. Set initial state and store cycle/respondent info
    # 4. Send the first question

    await callback.message.edit_text(
        f"Начинаем опрос (цикл: {cycle_id}, респондент: {respondent_id}).\n"
        "\n(Здесь будет логика анкеты...)"
    )
    await callback.answer()
