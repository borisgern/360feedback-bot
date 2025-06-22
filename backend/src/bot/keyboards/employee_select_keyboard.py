from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List

class EmployeeShort:
    def __init__(self, id: str, full_name: str):
        self.id = id
        self.full_name = full_name


def get_employee_select_keyboard(employees: List[EmployeeShort], page: int = 0, page_size: int = 10) -> InlineKeyboardMarkup:
    """
    Формирует клавиатуру для выбора сотрудника (по 10 на страницу).
    В callback_data кладём employee_id.
    """
    start = page * page_size
    end = start + page_size
    page_employees = employees[start:end]

    buttons = [
        [InlineKeyboardButton(text=emp.full_name, callback_data=f"select_target:{emp.id}")]
        for emp in page_employees
    ]

    navigation = []
    if start > 0:
        navigation.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"emp_page:{page-1}"))
    if end < len(employees):
        navigation.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"emp_page:{page+1}"))
    if navigation:
        buttons.append(navigation)

    return InlineKeyboardMarkup(inline_keyboard=buttons)
