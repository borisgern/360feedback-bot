import logging
from typing import List, Dict, Any

import openai
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

from ..config import Settings
from ..storage.models import FeedbackCycle
from .google_sheets import GoogleSheetsService
from .employee_service import EmployeeService
from .question_service import QuestionnaireService

logger = logging.getLogger(__name__)

# Question IDs for open-ended questions to be summarized by AI
STRENGTHS_QUESTION_ID = "O-2"
WEAKNESSES_QUESTION_ID = "O-1"


class ReportService:
    def __init__(
        self,
        g_sheets_service: GoogleSheetsService,
        employee_service: EmployeeService,
        questionnaire_service: QuestionnaireService,
        config: Settings,
    ):
        self._g_sheets = g_sheets_service
        self._employees = employee_service
        self._questionnaire = questionnaire_service
        self._config = config
        self._openai_client = openai.AsyncOpenAI(
            api_key=config.openai.API_KEY,
            base_url=config.openai.API_BASE,
        )

    async def _get_answers_for_cycle(self, cycle: FeedbackCycle) -> List[Dict[str, Any]]:
        """Fetches all answer records for a given cycle from its Google Sheet."""
        sheet_title = cycle.sheet_title
        if not sheet_title:
            # Backward compatibility for old cycles without a stored sheet_title.
            logger.warning(f"Cycle {cycle.id} is missing a sheet_title. Generating it based on old logic.")
            target_employee = self._employees.find_by_id(cycle.target_employee_id)
            if not target_employee:
                logger.error(f"Cannot get answers: target employee {cycle.target_employee_id} not found.")
                return []
            
            # This is the original logic from cycle_service.py
            timestamp_part = '_'.join(cycle.id.split('_')[:2])
            sheet_title = f"{timestamp_part}_{target_employee.full_name}"

        try:
            records = await self._g_sheets.get_all_records(sheet_title)
            return records
        except Exception as e:
            logger.error(f"Failed to get records from sheet '{sheet_title}': {e}")
            return []

    async def _get_employee_full_name(self, employee_id: str) -> str:
        target_employee = self._employees.find_by_id(employee_id)
        if not target_employee:
            logger.error(f"Cannot get employee for report: {employee_id} not found.")
            return ""
        return target_employee.full_name

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _summarize_with_ai(self, texts: List[str], topic: str, target_name: str) -> str:
        """Generates a summary for a list of texts using the OpenAI API."""
        if not texts:
            return "Ответы не найдены."

        filtered_texts = [text for text in texts if text and len(text.strip()) > 10]
        if not filtered_texts:
            return "Не найдено развернутых ответов для анализа."

        content = "\n".join(f"- {text}" for text in filtered_texts)
        prompt = (
            f"Проанализируй следующие анонимные отзывы о сотруднике по имени {target_name} на тему '{topic}'. "
            f"Сделай краткое, структурированное саммари (3-5 ключевых тезисов в виде буллет-поинтов). "
            f"Сохраняй нейтральный и объективный тон. Не делай предположений, основывайся только на предоставленном тексте. "
            f"Ответ дай на русском языке.\n\n"
            f"Отзывы:\n{content}"
        )

        response = await self._openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()

    async def generate_report_for_cycle(self, cycle: FeedbackCycle) -> str:
        """Generates a full summary report for a completed feedback cycle."""
        target_employee_name = await self._get_employee_full_name(cycle.target_employee_id)
        report_header = (
            f"<b>Отчет по циклу 360° для {target_employee_name}</b>\n"
            f"ID цикла: <code>{cycle.id}</code>\n"
        )

        all_answers = await self._get_answers_for_cycle(cycle)
        if not all_answers:
            return f"{report_header}\n⚠️ Не удалось получить ответы из Google Sheets."

        all_questions = await self._questionnaire.get_questionnaire()
        question_map = {q.id: q for q in all_questions}

        strengths_col = question_map.get(STRENGTHS_QUESTION_ID).result_column
        weaknesses_col = question_map.get(WEAKNESSES_QUESTION_ID).result_column

        strengths_texts = [str(ans[strengths_col]) for ans in all_answers if strengths_col in ans and ans[strengths_col]]
        weaknesses_texts = [str(ans[weaknesses_col]) for ans in all_answers if weaknesses_col in ans and ans[weaknesses_col]]

        try:
            strengths_summary = await self._summarize_with_ai(strengths_texts, "Сильные стороны", target_employee_name)
        except RetryError as e:
            logger.error(f"Failed to get AI summary for strengths after multiple retries: {e}")
            strengths_summary = "<i>Не удалось сгенерировать саммари по сильным сторонам из-за ошибки API.</i>"

        try:
            weaknesses_summary = await self._summarize_with_ai(weaknesses_texts, "Точки роста и блокеры", target_employee_name)
        except RetryError as e:
            logger.error(f"Failed to get AI summary for weaknesses after multiple retries: {e}")
            weaknesses_summary = "<i>Не удалось сгенерировать саммари по точкам роста из-за ошибки API.</i>"

        # TODO: Add calculation of average scores for competency questions
        # TODO: Add list of non-respondents

        report_body = (
            f"\n<b>Резюме на основе AI</b>\n\n"
            f"<b>Сильные стороны:</b>\n{strengths_summary}\n\n"
            f"<b>Точки роста и блокеры:</b>\n{weaknesses_summary}\n"
        )

        return report_header + report_body
