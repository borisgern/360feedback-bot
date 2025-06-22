import logging
from datetime import datetime
from aiogram.types import CallbackQuery

from aiogram import F, Router, types, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from ...config import settings
from ...services.cycle_service import CycleService
from ...services.employee_service import EmployeeService

from ..keyboards.admin_keyboards import get_confirmation_keyboard
from ..middlewares.auth import AdminAuthMiddleware
from ..states.cycle_creation import CycleCreationFSM

logger = logging.getLogger(__name__)

router = Router()
# Protect all handlers in this router with the admin auth middleware
router.message.middleware(AdminAuthMiddleware(settings.ADMIN_TELEGRAM_IDS))

MAX_ACTIVE_CYCLES = 5


@router.message(Command("new_cycle"), StateFilter(None))
async def cmd_new_cycle(
    message: types.Message,
    state: FSMContext,
    cycle_service: CycleService,
    employee_service: EmployeeService,
):
    """
    Handler for the /new_cycle command. Starts the cycle creation FSM.
    """
    active_cycles = await cycle_service.get_active_cycles_count()
    if active_cycles >= MAX_ACTIVE_CYCLES:
        await message.answer(
            f"Достигнут лимит активных циклов ({active_cycles}/{MAX_ACTIVE_CYCLES})."
        )
        return

    await employee_service.load_employees()

    await state.set_state(CycleCreationFSM.waiting_for_target_employee)

    # Prepare list of employees for selection
    from ..keyboards.employee_select_keyboard import get_employee_select_keyboard, EmployeeShort
    employees = [EmployeeShort(emp.id, emp.full_name) for emp in employee_service._employees]
    if not employees:
        await message.answer("В справочнике сотрудников нет записей.")
        return
    await message.answer(
        "Запускаем новый цикл сбора обратной связи.\n\nВыберите сотрудника-цель:",
        reply_markup=get_employee_select_keyboard(employees, page=0)
    )


@router.callback_query(lambda c: c.data.startswith("emp_page:"), CycleCreationFSM.waiting_for_target_employee)
async def paginate_employees(callback: CallbackQuery, state: FSMContext, employee_service: EmployeeService):
    page = int(callback.data.split(":")[1])
    from ..keyboards.employee_select_keyboard import get_employee_select_keyboard, EmployeeShort
    employees = [EmployeeShort(emp.id, emp.full_name) for emp in employee_service._employees]
    await callback.message.edit_reply_markup(reply_markup=get_employee_select_keyboard(employees, page=page))
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("select_target:"), CycleCreationFSM.waiting_for_target_employee)
async def select_target_employee(callback: CallbackQuery, state: FSMContext, employee_service: EmployeeService):
    employee_id = callback.data.split(":")[1]
    employee = employee_service.find_by_id(employee_id)
    if not employee:
        await callback.answer("Сотрудник не найден.", show_alert=True)
        return

    await state.update_data(target_employee_id=employee.id)
    await state.update_data(respondents=[])
    await state.set_state(CycleCreationFSM.waiting_for_respondents)

    # Prepare respondent selection keyboard
    from ..keyboards.respondent_select_keyboard import get_respondent_select_keyboard
    all_other_employees = [emp for emp in employee_service._employees if emp.id != employee.id]
    selected_respondents = set()

    await callback.message.edit_text(
        f"Отлично. Цель: <b>{employee.full_name}</b>.\n\n"
        "Теперь выберите респондентов (можно выбрать несколько).",
        reply_markup=get_respondent_select_keyboard(all_other_employees, selected_respondents)
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("resp_page:"), CycleCreationFSM.waiting_for_respondents)
async def paginate_respondents(callback: CallbackQuery, state: FSMContext, employee_service: EmployeeService):
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    target_employee_id = data.get("target_employee_id")
    target_employee = employee_service.find_by_id(target_employee_id)
    all_other_employees = [emp for emp in employee_service._employees if emp.id != target_employee.id]
    selected_respondents = set(data.get("respondents", []))

    from ..keyboards.respondent_select_keyboard import get_respondent_select_keyboard
    await callback.message.edit_reply_markup(
        reply_markup=get_respondent_select_keyboard(all_other_employees, selected_respondents, page=page)
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("toggle_resp:"), CycleCreationFSM.waiting_for_respondents)
async def toggle_respondent(callback: CallbackQuery, state: FSMContext, employee_service: EmployeeService):
    _, respondent_id, page_str = callback.data.split(":")
    page = int(page_str)

    data = await state.get_data()
    current_respondents = set(data.get("respondents", []))

    if respondent_id in current_respondents:
        current_respondents.remove(respondent_id)
    else:
        current_respondents.add(respondent_id)
    
    await state.update_data(respondents=list(current_respondents))

    # Re-render keyboard
    target_employee_id = data.get("target_employee_id")
    target_employee = employee_service.find_by_id(target_employee_id)
    all_other_employees = [emp for emp in employee_service._employees if emp.id != target_employee.id]
    
    from ..keyboards.respondent_select_keyboard import get_respondent_select_keyboard
    await callback.message.edit_reply_markup(
        reply_markup=get_respondent_select_keyboard(all_other_employees, current_respondents, page=page)
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("resp_select_all:"), CycleCreationFSM.waiting_for_respondents)
async def select_all_respondents(callback: CallbackQuery, state: FSMContext, employee_service: EmployeeService):
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    target_employee_id = data.get("target_employee_id")
    target_employee = employee_service.find_by_id(target_employee_id)
    all_other_employees = [emp for emp in employee_service._employees if emp.id != target_employee.id]
    
    all_respondent_ids = {emp.id for emp in all_other_employees}
    await state.update_data(respondents=list(all_respondent_ids))

    from ..keyboards.respondent_select_keyboard import get_respondent_select_keyboard
    await callback.message.edit_reply_markup(
        reply_markup=get_respondent_select_keyboard(all_other_employees, all_respondent_ids, page=page)
    )
    await callback.answer("Выбраны все респонденты")


@router.callback_query(lambda c: c.data.startswith("resp_deselect_all:"), CycleCreationFSM.waiting_for_respondents)
async def deselect_all_respondents(callback: CallbackQuery, state: FSMContext, employee_service: EmployeeService):
    page = int(callback.data.split(":")[1])
    await state.update_data(respondents=[])

    data = await state.get_data()
    target_employee_id = data.get("target_employee_id")
    target_employee = employee_service.find_by_id(target_employee_id)
    all_other_employees = [emp for emp in employee_service._employees if emp.id != target_employee.id]
    
    from ..keyboards.respondent_select_keyboard import get_respondent_select_keyboard
    await callback.message.edit_reply_markup(
        reply_markup=get_respondent_select_keyboard(all_other_employees, set(), page=page)
    )
    await callback.answer("Выбор снят со всех респондентов")


@router.callback_query(F.data == "finish_respondents", CycleCreationFSM.waiting_for_respondents)
async def finish_respondents_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("respondents"):
        await callback.answer("Нужно добавить хотя бы одного респондента.", show_alert=True)
        return

    await state.set_state(CycleCreationFSM.waiting_for_deadline)
    await callback.message.edit_text(
        "Ввод респондентов завершен.\n\nВведите дедлайн в формате ГГГГ-ММ-ДД:"
    )
    await callback.answer()


@router.message(CycleCreationFSM.waiting_for_deadline)
async def process_deadline(message: types.Message, state: FSMContext, employee_service: EmployeeService):
    try:
        deadline = datetime.strptime(message.text.strip(), "%Y-%m-%d").date()
        if deadline <= datetime.now().date():
            await message.answer("Дедлайн должен быть в будущем. Попробуйте еще раз.")
            return
    except ValueError:
        await message.answer("Неверный формат даты. Введите дату в формате ГГГГ-ММ-ДД.")
        return

    await state.update_data(deadline=deadline.isoformat())

    data = await state.get_data()
    target_employee_id = data.get("target_employee_id")
    target_employee = employee_service.find_by_id(target_employee_id)
    target_employee_name = target_employee.full_name
    respondents_count = len(data.get("respondents", []))

    summary = (
        f"<b>Подтвердите создание цикла:</b>\n\n"
        f"<b>Цель:</b> {target_employee_name}\n"
        f"<b>Кол-во респондентов:</b> {respondents_count}\n"
        f"<b>Дедлайн:</b> {deadline.strftime('%d.%m.%Y')}"
    )

    await state.set_state(CycleCreationFSM.confirming_creation)
    await message.answer(summary, reply_markup=get_confirmation_keyboard())


@router.callback_query(F.data == "cancel_creation", CycleCreationFSM.confirming_creation)
async def cancel_creation(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Создание цикла отменено.")
    await callback.answer()


@router.callback_query(F.data == "confirm_creation", CycleCreationFSM.confirming_creation)
async def confirm_creation(
    callback: types.CallbackQuery,
    state: FSMContext,
    cycle_service: CycleService,
    employee_service: EmployeeService,
    bot: Bot,
):
    await callback.message.edit_text("Создаем цикл... ")

    try:
        # Create the feedback cycle
        data = await state.get_data()
        target_employee_id = data.get("target_employee_id")
        respondent_ids = data.get("respondents")
        deadline = data.get("deadline")
        target_employee = employee_service.find_by_id(target_employee_id)
        cycle = await cycle_service.create_new_cycle(
            target_employee=target_employee,
            respondent_ids=respondent_ids,
            deadline=deadline,
        )
        # After successful creation, distribute the survey links
        await cycle_service.notify_respondents(
            cycle=cycle,
            employee_service=employee_service,
            bot=bot,
        )
        await callback.message.edit_text(
            f" Цикл <code>{cycle.id}</code> успешно создан и разослан респондентам."
        )
    except Exception as e:
        logger.error(f"Failed to create cycle: {e}", exc_info=True)
        await callback.message.edit_text(
            " Произошла ошибка при создании цикла. Попробуйте позже."
        )
    finally:
        await state.clear()
        await callback.answer()
