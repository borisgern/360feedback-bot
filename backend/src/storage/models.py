from datetime import date, datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Question(BaseModel):
    id: str = Field(alias="question_id")
    text: str = Field(alias="question_text")
    type: str = Field(alias="question_type")
    options: Optional[List[str]] = None  # For radio / checkbox
    required: bool = Field(default=False)
    result_column: Optional[str] = Field(alias="sheet_column", default=None)

    # We're not normalizing types anymore
    # @field_validator("type")
    # @classmethod
    # def validate_type(cls, v: str) -> str:
    #     """
    #     Normalize and validate question type.
    #     Accepts base types and normalizes variants like 'scale 0-3' to 'scale'.
    #     """
    #     v_lower = v.lower()
    #     base_types = {"text", "checkbox", "textarea", "radio", "choice"}
    #     if v_lower in base_types:
    #         return v_lower
    #     if v_lower.startswith("scale"):
    #         return "scale"
    #     raise ValueError(f"Unknown question type: {v}")


class Questionnaire(BaseModel):
    questions: List[Question]


class Employee(BaseModel):
    telegram_nickname: str = Field(alias="Telegram_Nickname")
    last_name: str = Field(alias="Last_Name")
    first_name: str = Field(alias="First_Name")
    telegram_id: Optional[int] = None

    @property
    def id(self) -> str:
        return self.telegram_nickname.lstrip("@")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class RespondentInfo(BaseModel):
    """Information about a respondent in a feedback cycle."""
    id: str
    status: Literal["pending", "completed"] = "pending"
    completed_at: Optional[datetime] = None


class FeedbackCycle(BaseModel):
    id: str
    target_employee_id: str
    respondents: Dict[str, RespondentInfo]  # key: respondent_id
    deadline: date
    status: Literal["active", "closed", "reported"] = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FeedbackDraft(BaseModel):
    cycle_id: str
    respondent_id: str
    answers: Dict[str, int | str] = {}  # key: question_id
