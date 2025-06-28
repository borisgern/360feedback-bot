from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault


async def set_bot_commands(bot: Bot):
    """Sets the bot commands in the Telegram menu."""
    commands = [
        BotCommand(command="new_cycle", description="Запустить новый цикл 360"),
        BotCommand(command="status", description="Посмотреть статусы активных циклов"),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())
