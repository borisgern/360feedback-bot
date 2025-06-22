from datetime import date, datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Question(BaseModel):
    id: str
    text: str
    type: Literal["scale", "text"]


class Questionnaire(BaseModel):
    questions: List[Question]


class Employee(BaseModel):
    id: str = Field(alias="Employee_ID")
    full_name: str = Field(alias="Full_Name")
    telegram_id: int = Field(alias="Telegram_ID")
    position: str = Field(alias="Position")
    manager_id: Optional[str] = Field(alias="Manager_ID")


class RespondentInfo(BaseModel):
    id: str
    status: Literal["pending", "completed"] = "pending"
    token: str


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
