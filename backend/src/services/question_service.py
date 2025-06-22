import logging
from typing import List, Optional

from pydantic import ValidationError

from ..storage.models import Question, Questionnaire
from ..storage.redis_storage import RedisStorageService
from .google_sheets import GoogleSheetsService

logger = logging.getLogger(__name__)

QUESTIONS_SHEET_NAME = "Questions"
QUESTIONS_CACHE_KEY = "questionnaire_v2"
QUESTIONS_CACHE_TTL_SECONDS = 3600  # 1 hour


class QuestionnaireService:
    def __init__(
        self,
        redis_service: RedisStorageService,
        google_sheets_service: GoogleSheetsService,
    ):
        self._redis = redis_service
        self._g_sheets = google_sheets_service

    async def get_questionnaire(self) -> Optional[List[Question]]:
        """
        Retrieves the questionnaire, from cache if available,
        otherwise from Google Sheets.
        """
        cached_questionnaire = await self._redis.get_model(
            QUESTIONS_CACHE_KEY, Questionnaire
        )
        if cached_questionnaire:
            logger.info("Questionnaire found in cache.")
            return cached_questionnaire.questions

        logger.info("Questionnaire not in cache, fetching from Google Sheets.")
        question_records = await self._g_sheets.get_all_records(QUESTIONS_SHEET_NAME)

        if not question_records:
            logger.error("No questions found in Google Sheets.")
            return None

        try:
            questions = [Question.model_validate(rec) for rec in question_records]
            questionnaire = Questionnaire(questions=questions)
            await self._redis.set_model(
                QUESTIONS_CACHE_KEY, questionnaire, ttl=QUESTIONS_CACHE_TTL_SECONDS
            )
            logger.info(f"Successfully fetched and cached {len(questions)} questions.")
            return questions
        except ValidationError as e:
            logger.error(f"Failed to validate questions from Google Sheets: {e}")
            return None
