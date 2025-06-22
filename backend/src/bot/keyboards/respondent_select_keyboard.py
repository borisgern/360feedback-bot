from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Set

from ...storage.models import Employee


def get_respondent_select_keyboard(
    all_employees: List[Employee],
    selected_ids: Set[str],
    page: int = 0,
    page_size: int = 10
) -> InlineKeyboardMarkup:
    """
    Generates a keyboard for selecting multiple respondents with pagination.
    """
    start = page * page_size
    end = start + page_size
    page_employees = all_employees[start:end]

    buttons = []
    action_buttons = [
        InlineKeyboardButton(text="Выбрать всех", callback_data=f"resp_select_all:{page}"),
        InlineKeyboardButton(text="Снять выбор", callback_data=f"resp_deselect_all:{page}")
    ]
    buttons.append(action_buttons)

    for emp in page_employees:
        text = f"✅ {emp.full_name}" if emp.id in selected_ids else emp.full_name
        buttons.append([
            InlineKeyboardButton(text=text, callback_data=f"toggle_resp:{emp.id}:{page}")
        ])

    navigation = []
    if start > 0:
        navigation.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"resp_page:{page-1}"))
    if end < len(all_employees):
        navigation.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"resp_page:{page+1}"))

    if navigation:
        buttons.append(navigation)

    buttons.append([
        InlineKeyboardButton(text="✅ Готово", callback_data="finish_respondents")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
