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
        # Debugging
        logger.info(f"Sending question {current_question_index}: id={question.id}, type={question.type}")
        logger.info(f"Question options: {question.options}")
        
        question_text_to_send = question.text.format(Имя=target_name)

        # Build appropriate keyboard based on question type
        keyboard = None
        # Check for scale type
        if question.type == "scale" or question.type.lower().startswith("scale"):
            logger.info(f"Creating scale keyboard for type: {question.type}")
            if question.options and question.options[0]:
                # The bot is initialized with HTML parse mode
                question_text_to_send += f"\n\n<i>{question.options[0]}</i>"
            # We assume scale 0-3. The button values are not from options.
            scale_values = ["0", "1", "2", "3"]
            buttons = [types.InlineKeyboardButton(text=v, callback_data=f"ans:{current_question_index}:{v}") for v in scale_values]
            # single row of buttons
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[buttons])
            logger.info(f"Scale keyboard created with values: {scale_values}")
        elif (question.type == "radio" or question.type == "checkbox") and question.options:
            logger.info("Creating radio keyboard")
            rows = [
                [types.InlineKeyboardButton(text=opt, callback_data=f"ans:{current_question_index}:{opt}")]
                for opt in question.options
            ]
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=rows)
            logger.info(f"Radio keyboard created with options: {question.options}")
        else:
            logger.info(f"No keyboard created for question type '{question.type}' with options: {question.options}. Fallback to text input.")
        # For textarea / checkbox fallback to plain text input
        
        logger.info(f"Keyboard for question: {keyboard is not None}")
        await message.answer(question_text_to_send, reply_markup=keyboard)
    else:
        # This case should ideally not be reached if the flow is correct
        logger.error("Attempted to send question beyond questionnaire bounds.")
        await message.answer("Опрос завершен. Спасибо!")
        await state.clear()


@router.message(CommandStart())
async def cmd_start(message: types.Message, employee_service: EmployeeService, cycle_service: CycleService, bot: Bot):
    telegram_id = message.from_user.id
    logger.info(f"Received /start command from telegram_id: {telegram_id}")

    telegram_id = message.from_user.id
    username = message.from_user.username

    logger.info(f"/start command from user: id={telegram_id}, username='{username}'")

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


@router.callback_query(SurveyStates.in_survey, F.data.startswith("ans:"))
async def process_answer_cb(
    callback: types.CallbackQuery,
    state: FSMContext,
    cycle_service: CycleService,
    employee_service: EmployeeService,
    bot: Bot,
):
    """Handles answer coming from inline keyboard buttons."""
    try:
        _, q_index_str, answer_val = callback.data.split(":", 2)
        q_index = int(q_index_str)
    except ValueError:
        await callback.answer("Неверный формат ответа", show_alert=True)
        return

    data = await state.get_data()
    raw_questions = data.get("questions", [])
    questions: List[Question] = [q if isinstance(q, Question) else Question.model_validate(q) for q in raw_questions]
    current_question_index = data.get("current_question_index", 0)

    # Ignore if callback for other question
    if q_index != current_question_index:
        await callback.answer()
        return

    answers = data.get("answers", [])
    current_question = questions[current_question_index]
    answers.append({"question_id": current_question.id, "answer": answer_val})

    # move on
    next_question_index = current_question_index + 1
    await state.update_data(answers=answers, current_question_index=next_question_index)

    if next_question_index < len(questions):
        await _send_question(callback.message, state)
    else:
        # same completion logic as text handler
        cycle_id = data.get("cycle_id")
        respondent_id = data.get("respondent_id")
        respondent = employee_service.find_by_telegram_id(callback.from_user.id) or employee_service.find_by_id(respondent_id)
        if not respondent:
            logger.error("Failed to save answers: respondent not found")
            await callback.message.answer("Ошибка при сохранении ответов. Обратитесь к администратору.")
            await state.clear()
            await callback.answer()
            return
        answers_dict = {item["question_id"]: item["answer"] for item in answers}
        try:
            await cycle_service.save_answers(
                cycle_id=cycle_id,
                respondent_id=respondent_id,
                answers=answers_dict,
                employee_service=employee_service,
                bot=bot,
            )
            await callback.message.answer("✨ Спасибо за ваши ответы! ✨")
        except Exception as e:
            logger.error(f"Failed to save answers: {e}")
            await callback.message.answer("Ошибка при сохранении ответов.")
        finally:
            await state.clear()
    await callback.answer()


@router.message(SurveyStates.in_survey)
async def process_answer(
    message: types.Message,
    state: FSMContext,
    cycle_service: CycleService,
    employee_service: EmployeeService,
    bot: Bot,
):
    """
    Processes a respondent's answer, saves it, and sends the next question.
    """
    data = await state.get_data()
    raw_questions = data.get("questions", [])
    questions: List[Question] = [q if isinstance(q, Question) else Question.model_validate(q) for q in raw_questions]
    current_question_index = data.get("current_question_index", 0)
    answers = data.get("answers", [])

    current_question = questions[current_question_index]

    # Only accept free-text for textarea questions
    if current_question.type not in {"text", "textarea"}:
        logger.warning(f"User sent text for a non-text question (type: {current_question.type}). Resending question.")
        await message.answer("Для этого вопроса, пожалуйста, используйте кнопки. Попробую отправить его еще раз.")
        await _send_question(message, state)
        return

    # Save the answer
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
                bot=bot,
            )
            await message.answer("✨ Спасибо за ваши ответы! Вы помогли коллеге стать лучше. ✨")
        except Exception as e:
            logger.error(f"Failed to save answers for cycle {cycle_id} for respondent {respondent.id}: {e}", exc_info=True)
            await message.answer("Произошла ошибка при сохранении ваших ответов. Пожалуйста, свяжитесь с администратором.")
        finally:
            await state.clear()
