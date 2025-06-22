import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio.client import Redis

from .bot.handlers import admin, respondent
from .config import settings
from .services.google_sheets import GoogleSheetsService
from .services.question_service import QuestionnaireService
from .storage.redis_storage import RedisStorageService


async def main():
    """
    Application entry point.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    # Initialize Bot and Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML")
    )

    # Initialize Redis storage
    redis_client = Redis.from_url(settings.redis.dsn)
    fsm_storage = RedisStorage(redis=redis_client)
    app_storage = RedisStorageService(redis_client=redis_client)

    # Initialize services
    google_sheets_service = GoogleSheetsService(config=settings.google)
    questionnaire_service = QuestionnaireService(
        redis_service=app_storage,
        google_sheets_service=google_sheets_service,
    )

    dp = Dispatcher(
        storage=fsm_storage,
        # Pass services to handlers
        g_sheets=google_sheets_service,
        app_storage=app_storage,
        questionnaire_service=questionnaire_service,
    )

    # Register routers
    dp.include_router(admin.router)
    dp.include_router(respondent.router)

    # Start polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(main())
