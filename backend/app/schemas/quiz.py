from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ---------- Users ----------
class UserCreate(BaseModel):
    email: str


class UserOut(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


# ---------- Documents ----------
class DocumentOut(BaseModel):
    id: int
    filename: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Quiz generation request ----------
class QuizGenerateRequest(BaseModel):
    document_id: int
    num_questions: int = Field(ge=1, le=30)
    # V2: "easy" | "medium" | "hard" | "mixed" (default). The AI service
    # interprets "mixed" as a spread across all three difficulty levels.
    difficulty: str = "mixed"
    # V2: chosen directly by the user, same as num_questions - not derived
    # from question count. Defaults to 10 minutes if the client omits it.
    time_limit_minutes: int = Field(default=10, ge=1, le=120)


class OptionOut(BaseModel):
    option_index: int
    option_text: str

    class Config:
        from_attributes = True


class QuestionOut(BaseModel):
    id: int
    question_text: str
    options: List[OptionOut]
    topic: Optional[str] = None
    difficulty: Optional[str] = None

    class Config:
        from_attributes = True


class QuizOut(BaseModel):
    id: int
    quiz_number: int
    num_questions: int
    time_limit_seconds: int
    questions: List[QuestionOut]

    class Config:
        from_attributes = True


# ---------- Raw AI structured output (internal validation) ----------
class AIQuestion(BaseModel):
    question: str
    options: List[str]
    correct_option: int
    explanation: str
    topic: str
    difficulty: str


class AIQuizResponse(BaseModel):
    questions: List[AIQuestion]


# ---------- Attempts ----------
class AttemptStartRequest(BaseModel):
    quiz_id: int
    user_id: int


class AttemptStartOut(BaseModel):
    attempt_id: int
    quiz: QuizOut


class AnswerSubmit(BaseModel):
    question_id: int
    selected_option_index: int


class AttemptSubmitRequest(BaseModel):
    answers: List[AnswerSubmit]


class AnswerReview(BaseModel):
    question_id: int
    question_text: str
    selected_option_index: int
    correct_option_index: int
    is_correct: bool
    explanation: Optional[str] = None


class AttemptResultOut(BaseModel):
    attempt_id: int
    score: int
    total_questions: int
    percentage: float
    answers: List[AnswerReview]


class AttemptHistoryItem(BaseModel):
    attempt_id: int = Field(validation_alias="id")
    quiz_id: int
    document_filename: Optional[str] = None
    quiz_number: Optional[int] = None
    score: Optional[int]
    total_questions: Optional[int]
    completed_at: Optional[datetime]
    is_completed: bool

    class Config:
        from_attributes = True
        populate_by_name = True


# ---------- V3: Performance Analytics ----------
class TopicStat(BaseModel):
    topic: str
    total_answered: int
    correct: int
    accuracy_percentage: float
    is_weak: bool


class OverviewStats(BaseModel):
    total_attempts: int
    total_questions_answered: int
    total_correct: int
    overall_accuracy_percentage: float
    recent_attempts: List[AttemptHistoryItem]
