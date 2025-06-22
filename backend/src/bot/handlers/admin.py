from aiogram import Router, types
from aiogram.filters import Command

router = Router()

# This router should be protected by the AdminAuthMiddleware


@router.message(Command("new_cycle"))
async def cmd_new_cycle(message: types.Message):
    """
    Handler for the /new_cycle command. Starts the cycle creation FSM.
    """
    await message.answer("Starting new feedback cycle creation...")
    # TODO: Start FSM for cycle creation
