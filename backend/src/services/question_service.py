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
            processed_records = []
            for rec in question_records:
                # Process options field if it exists
                if "options" in rec:
                    options_str = rec["options"]
                    # Handle empty options
                    if not options_str or options_str == "":
                        rec["options"] = []  # Empty list for no options
                        logger.info(f"Empty options for question {rec.get('question_id')}, setting to empty list")
                    # Process non-empty options
                    elif isinstance(options_str, str):
                        if ";" in options_str:
                            rec["options"] = [opt.strip() for opt in options_str.split(";") if opt.strip()]
                        elif "," in options_str:
                            rec["options"] = [opt.strip() for opt in options_str.split(",") if opt.strip()]
                        else:
                            rec["options"] = [options_str.strip()]
                        logger.info(f"Parsed options for question {rec.get('question_id')}: {rec['options']}")
                    else:
                        rec["options"] = []  # Fallback to empty list
                        logger.info(f"Invalid options for question {rec.get('question_id')}, setting to empty list")
                else:
                    # If options field doesn't exist, set it to empty list
                    rec["options"] = []
                
                # Process required field
                if "required" in rec:
                    if isinstance(rec["required"], str):
                        req_val = rec["required"].strip().lower()
                        rec["required"] = (
                            req_val in ["yes", "true", "да", "1"]
                            or req_val.startswith("да")
                            or req_val.startswith("yes")
                            or req_val.startswith("true")
                        )
                    else:
                        rec["required"] = bool(rec["required"])
                
                processed_records.append(rec)
                
            logger.info(f"Processed question records: {processed_records}")
            questions = [Question.model_validate(rec) for rec in processed_records]
            questionnaire = Questionnaire(questions=questions)
            await self._redis.set_model(
                QUESTIONS_CACHE_KEY, questionnaire, ttl=QUESTIONS_CACHE_TTL_SECONDS
            )
            logger.info(f"Successfully fetched and cached {len(questions)} questions.")
            return questions
        except ValidationError as e:
            logger.error(f"Failed to validate questions from Google Sheets: {e}")
            return None
