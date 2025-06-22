from aiogram import Router, types
from aiogram.filters import Command

from ...config import settings
from ..middlewares.auth import AdminAuthMiddleware

router = Router()
# Protect all handlers in this router with the admin auth middleware
router.message.middleware(AdminAuthMiddleware(settings.ADMIN_TELEGRAM_IDS))

# This router should be protected by the AdminAuthMiddleware


@router.message(Command("new_cycle"))
async def cmd_new_cycle(message: types.Message):
    """
    Handler for the /new_cycle command. Starts the cycle creation FSM.
    """
    await message.answer("Starting new feedback cycle creation...")
    # TODO: Start FSM for cycle creation
