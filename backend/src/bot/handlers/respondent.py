import logging
from typing import List

from aiogram import F, Router, types, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ...services.cycle_service import CycleService
from ...services.employee_service import EmployeeService
from ...services.question_service import QuestionnaireService
from ...storage.models import Question

logger = logging.getLogger(__name__)
router = Router()


class SurveyStates(StatesGroup):
    in_survey = State()


async def _send_question(message: types.Message, state: FSMContext):
    """Sends the current question to the respondent."""
    data = await state.get_data()
    raw_questions = data.get("questions", [])
    questions: List[Question] = [q if isinstance(q, Question) else Question.model_validate(q) for q in raw_questions]
    current_question_index: int = data.get("current_question_index", 0)
    target_name: str = data.get("target_employee_name", "коллеги")

    if current_question_index < len(questions):
        question = questions[current_question_index]
        # TODO: Add support for different question UI types (keyboards, etc.)
        await message.answer(question.text.format(Имя=target_name))
    else:
        # This case should ideally not be reached if the flow is correct
        logger.error("Attempted to send question beyond questionnaire bounds.")
        await message.answer("Опрос завершен. Спасибо!")
        await state.clear()


@router.message(CommandStart())
async def cmd_start(message: types.Message, employee_service: EmployeeService, cycle_service: CycleService, bot: Bot):
    telegram_id = message.from_user.id
    logger.info(f"Received /start command from telegram_id: {telegram_id}")

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
async def start_survey(
    callback: types.CallbackQuery,
    state: FSMContext,
    questionnaire_service: QuestionnaireService,
    cycle_service: CycleService,
    employee_service: EmployeeService,
):
    """
    Handles the 'Start Survey' button click, starting the questionnaire FSM.
    """
    _, cycle_id, respondent_id = callback.data.split(":")
    logger.info(f"Starting survey for cycle_id={cycle_id}, respondent_id={respondent_id}")

    cycle = await cycle_service.get_cycle_by_id(cycle_id)
    if not cycle:
        logger.error(f"Cannot start survey: cycle {cycle_id} not found.")
        await callback.message.edit_text("Произошла ошибка: не удалось найти информацию о цикле опроса.")
        await callback.answer()
        return

    target_employee = employee_service.find_by_id(cycle.target_employee_id)
    if not target_employee:
        logger.error(f"Cannot start survey: target employee {cycle.target_employee_id} not found.")
        await callback.message.edit_text("Произошла ошибка: не удалось найти сотрудника, о котором проводится опрос.")
        await callback.answer()
        return

    questionnaire = await questionnaire_service.get_questionnaire()
    if not questionnaire:
        logger.error(f"Cannot start survey for cycle {cycle_id}: questionnaire is empty.")
        await callback.message.edit_text("Не удалось загрузить анкету. Пожалуйста, попробуйте позже.")
        await callback.answer()
        return

    # Convert Pydantic models to plain dicts so they can be stored in FSM JSON storage
    serialized_questions = [q.model_dump(by_alias=True) for q in questionnaire]
    await state.set_state(SurveyStates.in_survey)
    await state.update_data(
        cycle_id=cycle_id,
        respondent_id=respondent_id,
        questions=serialized_questions,
        answers=[],
        current_question_index=0,
        target_employee_name=target_employee.first_name,
    )

    await callback.message.edit_text("Начинаем опрос. Пожалуйста, отвечайте на вопросы развернуто.")
    await _send_question(callback.message, state)
    await callback.answer()







@router.message(SurveyStates.in_survey)
async def process_answer(
    message: types.Message,
    state: FSMContext,
    cycle_service: CycleService,
    employee_service: EmployeeService,
):
    """
    Processes a respondent's answer, saves it, and sends the next question.
    """
    data = await state.get_data()
    raw_questions = data.get("questions", [])
    questions: List[Question] = [q if isinstance(q, Question) else Question.model_validate(q) for q in raw_questions]
    current_question_index = data.get("current_question_index", 0)
    answers = data.get("answers", [])

    # Save the answer for the current question
    current_question = questions[current_question_index]
    answers.append({"question_id": current_question.id, "answer": message.text})
    logger.info(f"Received answer for question '{current_question.id}'")

    # Move to the next question
    next_question_index = current_question_index + 1
    await state.update_data(
        answers=answers, current_question_index=next_question_index
    )

    if next_question_index < len(questions):
        # Send the next question
        await _send_question(message, state)
    else:
        # All questions answered, complete the survey
        cycle_id = data.get("cycle_id")
        respondent_id = data.get("respondent_id")
        
        # We need the full employee object to save answers correctly
        respondent = employee_service.find_by_telegram_id(message.from_user.id)
        if not respondent:
            logger.warning(f"Could not find respondent by telegram_id {message.from_user.id}, falling back to respondent_id {respondent_id}")
            respondent = employee_service.find_by_id(respondent_id)

        if not respondent:
            logger.error(f"Failed to save answers for cycle {cycle_id}: could not find respondent with id {respondent_id}.")
            await message.answer("Произошла критическая ошибка: не удалось найти ваш профиль для сохранения ответов. Обратитесь к администратору.")
            await state.clear()
            return

        logger.info(f"Completing survey for cycle {cycle_id} by respondent {respondent.id}.")

        # Convert list of answers to a dictionary for saving
        answers_dict = {item["question_id"]: item["answer"] for item in answers}

        try:
            await cycle_service.save_answers(
                cycle_id=cycle_id,
                respondent_id=respondent_id,
                answers=answers_dict,
                employee_service=employee_service,
            )
            await message.answer("✨ Спасибо за ваши ответы! Вы помогли коллеге стать лучше. ✨")
        except Exception as e:
            logger.error(f"Failed to save answers for cycle {cycle_id} for respondent {respondent.id}: {e}", exc_info=True)
            await message.answer("Произошла ошибка при сохранении ваших ответов. Пожалуйста, свяжитесь с администратором.")
        finally:
            await state.clear()
