from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Returns a keyboard for confirming or canceling an action."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_creation"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_creation"),
            ]
        ]
    )
