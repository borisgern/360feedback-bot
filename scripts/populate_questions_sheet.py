import os
import gspread
from dotenv import load_dotenv

# --- Configuration ---
# This list is generated based on the updated docs/spec_360_feedback_bot.md
QUESTIONS_DATA = [
    # General
    {"id": "G-1", "ui_type": "checkbox", "text": "Комфортно ли тебе работать с «{Имя}»?", "options": "communication,flexibility,responsibility,openness,teamwork", "is_required": "да (≥ 1 чек)", "sheet_column": "G1_comfort"},
    {"id": "G-1-c", "ui_type": "textarea", "text": "Дополнительный комментарий", "options": "", "is_required": "нет", "sheet_column": "G1_comment"},
    {"id": "G-2", "ui_type": "radio", "text": "Соответствует ли «{Имя}» своей экспертизе и роли?", "options": "yes,no,unknown", "is_required": "да", "sheet_column": "G2_role_fit"},
    # Competencies
    {"id": "C-1", "ui_type": "scale 0-3", "text": "Ориентация на результат [Ownership]", "options": "0 → «мин. результат» … 3 → «учитывает влияние на другие процессы»", "is_required": "да", "sheet_column": "C1_score"},
    {"id": "C-1-c", "ui_type": "textarea", "text": "Пример по «Ownership»", "options": "", "is_required": "нет", "sheet_column": "C1_comment"},
    {"id": "C-2", "ui_type": "scale 0-3", "text": "Ориентация на потребности клиента", "options": "0 → «не учитывает» … 3 → «предвосхищает»", "is_required": "да", "sheet_column": "C2_score"},
    {"id": "C-2-c", "ui_type": "textarea", "text": "Пример по «Клиент»", "options": "", "is_required": "нет", "sheet_column": "C2_comment"},
    {"id": "C-3", "ui_type": "scale 0-3", "text": "Ведение переговоров", "options": "0 → «не достигает целей» … 3 → «win-win»", "is_required": "да", "sheet_column": "C3_score"},
    {"id": "C-3-c", "ui_type": "textarea", "text": "Пример по «Переговоры»", "options": "", "is_required": "нет", "sheet_column": "C3_comment"},
    {"id": "C-4", "ui_type": "scale 0-3", "text": "Управление конфликтами", "options": "0 → «неконструктив / избегает» … 3 → «конструктивно решает»", "is_required": "да", "sheet_column": "C4_score"},
    {"id": "C-4-c", "ui_type": "textarea", "text": "Пример по «Конфликты»", "options": "", "is_required": "нет", "sheet_column": "C4_comment"},
    {"id": "C-5", "ui_type": "scale 0-3", "text": "Определение приоритетов", "options": "0 → «теряет фокус» … 3 → «правильно расставляет»", "is_required": "да", "sheet_column": "C5_score"},
    {"id": "C-5-c", "ui_type": "textarea", "text": "Пример по «Приоритеты»", "options": "", "is_required": "нет", "sheet_column": "C5_comment"},
    {"id": "C-6", "ui_type": "scale 0-3", "text": "Формирование эффективных команд", "options": "0 → «нет командности» … 3 → «формирует команды»", "is_required": "да", "sheet_column": "C6_score"},
    {"id": "C-6-c", "ui_type": "textarea", "text": "Пример по «Команды»", "options": "", "is_required": "нет", "sheet_column": "C6_comment"},
    {"id": "C-7", "ui_type": "scale 0-3", "text": "Воспроизводство практики и развитие команды", "options": "0 → «тормозит развитие» … 3 → «помогает расти»", "is_required": "да", "sheet_column": "C7_score"},
    {"id": "C-7-c", "ui_type": "textarea", "text": "Пример по «Развитие»", "options": "", "is_required": "нет", "sheet_column": "C7_comment"},
    {"id": "C-8", "ui_type": "scale 0-3", "text": "Действия в неопределённости и решение проблем", "options": "0 → «сопротивляется изменениям» … 3 → «инициирует решения»", "is_required": "да", "sheet_column": "C8_score"},
    {"id": "C-8-c", "ui_type": "textarea", "text": "Пример по «Неопределённость»", "options": "", "is_required": "нет", "sheet_column": "C8_comment"},
    # Outcome
    {"id": "O-1", "ui_type": "textarea", "text": "Блокеры / несоответствия позиции", "options": "", "is_required": "да", "sheet_column": "O1_blockers"},
    {"id": "O-2", "ui_type": "textarea", "text": "Сильные стороны", "options": "", "is_required": "да", "sheet_column": "O2_strengths"},
    {"id": "O-3", "ui_type": "textarea", "text": "Предложения и пожелания «{Имя}»", "options": "", "is_required": "нет", "sheet_column": "O3_suggestions"},
]

QUESTIONS_SHEET_NAME = "Questions"

def main():
    """Main function to populate the Google Sheet with questions."""
    print("Starting script to populate Google Sheet with updated questions...")

    # Load environment variables from .env file in the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(project_root, '.env'))

    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    key_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_PATH")

    if not sheet_id or not key_path:
        print("Error: GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_KEY_PATH must be set in .env file.")
        return

    # Adjust key path to be absolute from project root if it's relative
    if not os.path.isabs(key_path):
        key_path = os.path.join(project_root, key_path)

    if not os.path.exists(key_path):
        print(f"Error: Service account key file not found at {key_path}")
        return

    try:
        # Authenticate with Google Sheets
        gc = gspread.service_account(filename=key_path)
        spreadsheet = gc.open_by_key(sheet_id)
        print(f"Successfully opened spreadsheet: '{spreadsheet.title}'")

        # Get or create the worksheet
        try:
            worksheet = spreadsheet.worksheet(QUESTIONS_SHEET_NAME)
            print(f"Worksheet '{QUESTIONS_SHEET_NAME}' found. Clearing it before writing new data.")
            worksheet.clear()
        except gspread.WorksheetNotFound:
            print(f"Worksheet '{QUESTIONS_SHEET_NAME}' not found. Creating a new one.")
            worksheet = spreadsheet.add_worksheet(title=QUESTIONS_SHEET_NAME, rows=len(QUESTIONS_DATA) + 1, cols=len(QUESTIONS_DATA[0]))

        # Prepare data for upload
        header = list(QUESTIONS_DATA[0].keys())
        rows = [list(q.values()) for q in QUESTIONS_DATA]

        # Write to sheet
        worksheet.append_row(header, value_input_option='RAW')
        worksheet.append_rows(rows, value_input_option='RAW')

        print(f"Successfully wrote {len(rows)} questions to '{QUESTIONS_SHEET_NAME}'.")
        print("Script finished.")

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Error: Spreadsheet with ID '{sheet_id}' not found. Check your GOOGLE_SHEET_ID.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()