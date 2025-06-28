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
    async def _summarize_with_ai(self, texts: List[str], target_name: str) -> str:
        """Generates a full report based on a list of texts using the OpenAI API."""
        if not texts:
            return "Ответы не найдены."

        filtered_texts = [text for text in texts if text and len(text.strip()) > 10]
        if not filtered_texts:
            return "Не найдено развернутых ответов для анализа."

        content = "\n".join(filtered_texts)
        prompt = (
            f"ты — hr-аналитик rad mad robot.\n"
            f"задача: на основе анонимных 360-ответов сформировать персональный отчёт для робота {target_name}.\n\n"
            f"контекст\n"
            f"тема опроса: «сильные стороны и зоны роста».\n"
            f"ниже, в тегах <review>, даны сыровые ответы других роботов.\n"
            f"ориентируйся на структуру sample report — смотри раздел «пример» дальше.\n\n"
            f"ограничения\n"
            f"1. в разделе «цитаты роботов» возьми 2-3 ПОДСТРОЧНЫЕ цитаты из текста между <review>…</review>.\n"
            f"   - копируй БЕЗ ИЗМЕНЕНИЙ: символы, регистр, пунктуация — всё сохраняй;\n"
            f"   - если цитата длиннее 20 слов, воспользуйся многоточием внутри («…») без правки остального текста.\n"
            f"   - вот пример:\n"
            f"     ✔ надо: «я люблю баг-фиксы, потому что это вызов»\n"
            f"     ✖ нельзя: «робот любит чинить баги, это вызов»\n"
            f"2. не используй слова «коллега/коллеги», только «робот/роботы».\n"
            f"3. не указывай имена или номера респондентов.\n"
            f"4. не добавляй фактов сверх текста.\n"
            f"5. стиль: дружелюбно, без воды, строчные буквы.\n"
            f"6. итоговый отчёт ≤ 400 слов, markdown-блок.\n\n"
            f"---\n"
            f"### пример (sample report — копируй заголовки)\n\n"
            f"**краткое summary**\n"
            f"роботы ценят, что анна быстро находит решения…\n\n"
            f"**сильные стороны**\n"
            f"🚀 скорость…\n"
            f"🤝 открытость…\n"
            f"🎯 фокус…\n\n"
            f"**зоны роста**\n"
            f"развивай регулярное делегирование…\n"
            f"развивай стратегическое планирование…\n"
            f"развивай вовлечение команды…\n\n"
            f"**цитаты роботов**\n"
            f"«если надо “пожар” — анна первая на месте»\n"
            f"«иногда берёт слишком много на себя»\n"
            f"«клёво, что всегда обратная связь по делу»\n\n"
            f"**план действий 30-60-90**\n"
            f"30 дней: настроить…\n"
            f"60 дней: провести…\n"
            f"90 дней: отследить…\n\n"
            f"---\n"
            f"### отзывы\n"
            f"<review>\n"
            f"{content}\n"
            f"</review>"
        )

        response = await self._openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()

    async def generate_report_for_cycle(self, cycle: FeedbackCycle) -> str:
        """Generates a full summary report for a completed feedback cycle."""
        target_employee_name = await self._get_employee_full_name(cycle.target_employee_id)
        report_header = (
            f"**Отчет по циклу 360° для {target_employee_name}**\n"
            f"ID цикла: `{cycle.id}`\n"
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

        all_feedback_texts = strengths_texts + weaknesses_texts

        try:
            ai_summary = await self._summarize_with_ai(all_feedback_texts, target_employee_name)
        except RetryError as e:
            logger.error(f"Failed to get AI summary after multiple retries: {e}")
            ai_summary = "_Не удалось сгенерировать AI-отчет из-за ошибки API._"

        # TODO: Add calculation of average scores for competency questions
        # TODO: Add list of non-respondents

        report_body = f"\n{ai_summary}\n"

        return report_header + report_body
