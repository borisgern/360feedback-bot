from aiogram import F, Router, types
from aiogram.filters import CommandStart

router = Router()


@router.message(CommandStart(deep_link=True))
async def cmd_start_with_token(message: types.Message):
    """
    Handler for start links with a feedback token.
    e.g., t.me/bot?start=<token>
    """
    token = message.text.split(" ")[1]
    await message.answer(f"Welcome! You are starting feedback with token: {token}")
    # TODO: Validate token and start questionnaire FSM
