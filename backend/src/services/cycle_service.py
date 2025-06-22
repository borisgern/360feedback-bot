import logging
import uuid
from datetime import date, datetime

from ..storage.models import Employee, FeedbackCycle, RespondentInfo, TokenData
from ..storage.redis_storage import RedisStorageService
from .google_sheets import GoogleSheetsService
from .question_service import QuestionnaireService

logger = logging.getLogger(__name__)

class CycleService:
    def __init__(
        self,
        redis_service: RedisStorageService,
        google_sheets_service: GoogleSheetsService,
        questionnaire_service: QuestionnaireService,
    ):
        self._redis = redis_service
        self._g_sheets = google_sheets_service
        self._questionnaire = questionnaire_service

    async def get_active_cycles_count(self) -> int:
        """
        Returns the number of active feedback cycles.
        Note: This is a simplified implementation. A more robust solution would
        involve fetching each cycle and checking its status or using a dedicated
        set in Redis for active cycle IDs.
        """
        keys = await self._redis.get_keys_by_pattern("cycle:*")
        return len(keys)

    async def create_new_cycle(
        self, target_employee: Employee, respondent_ids: list[str], deadline: date
    ) -> FeedbackCycle:
        """Creates a new feedback cycle, stores it, and sets up the results sheet."""
        cycle_id = f"{datetime.now().strftime('%Y%m%d')}_{target_employee.id}"

        respondents = {}
        for resp_id in respondent_ids:
            token = str(uuid.uuid4())
            respondents[resp_id] = RespondentInfo(id=resp_id, token=token)
            # Store token -> user mapping for easy lookup on /start <token>
            token_data = TokenData(cycle_id=cycle_id, respondent_id=resp_id)
            await self._redis.set_model(f"token:{token}", token_data)

        cycle = FeedbackCycle(
            id=cycle_id,
            target_employee_id=target_employee.id,
            respondents=respondents,
            deadline=deadline,
        )

        await self._redis.set_model(f"cycle:{cycle.id}", cycle)

        sheet_title = f"{datetime.now().strftime('%Y-%m-%d')}_{target_employee.full_name}"
        questions = await self._questionnaire.get_questionnaire()
        if not questions:
            # This can happen if the Questions sheet is empty or validation fails.
            raise ValueError("Could not retrieve questionnaire to create cycle.")
        headers = ["cycle_id", "respondent_id", "submitted_at"] + [
            q.id for q in questions
        ]
        await self._g_sheets.create_worksheet(sheet_title, headers)

        logger.info(f"Successfully created feedback cycle {cycle_id}")
        return cycle
