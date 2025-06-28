from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List

from ...storage.models import FeedbackCycle
from ...services.employee_service import EmployeeService


def get_cycle_list_keyboard(cycles: List[FeedbackCycle], employee_service: EmployeeService) -> InlineKeyboardMarkup:
    """Generate a keyboard with buttons for each cycle."""
    buttons = []
    for cycle in sorted(cycles, key=lambda c: c.created_at, reverse=True):
        target = employee_service.find_by_id(cycle.target_employee_id)
        if target:
            sheet_title = f"{cycle.created_at.strftime('%Y%m%d_%H%M%S')}_{target.full_name}"
        else:
            sheet_title = cycle.id
        buttons.append([
            InlineKeyboardButton(
                text=sheet_title,
                callback_data=f"cycle_status:{cycle.id}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
