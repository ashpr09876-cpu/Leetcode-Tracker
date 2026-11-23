from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Difficulty = Literal["easy", "medium", "hard"]
Status = Literal["attempted", "solved", "needs_revision", "mastered"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth / users
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PreferencesOut(ORM):
    theme: str
    daily_goal: int
    notifications_enabled: bool
    ai_provider: str
    revision_intervals: list[int]


class PreferencesIn(BaseModel):
    theme: Literal["light", "dark", "system"] | None = None
    daily_goal: int | None = Field(default=None, ge=0, le=100)
    notifications_enabled: bool | None = None
    ai_provider: Literal["", "gemini", "openai", "anthropic", "ollama"] | None = None
    revision_intervals: list[int] | None = None

    @field_validator("revision_intervals")
    @classmethod
    def _intervals(cls, v):
        if v is not None and (not v or len(v) > 12 or any(i < 1 or i > 730 for i in v)):
            raise ValueError("Provide 1-12 intervals between 1 and 730 days")
        return v


class UserOut(ORM):
    id: int
    email: str
    name: str
    is_admin: bool
    timezone: str
    leetcode_username: str | None
    has_password: bool = True
    preferences: PreferencesOut | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    timezone: str | None = None
    leetcode_username: str | None = Field(default=None, max_length=100)
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=128)
    preferences: PreferencesIn | None = None


# ---- topics / companies
class TopicIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class TopicOut(ORM):
    id: int
    name: str
    is_default: bool


class CompanyOut(BaseModel):
    id: int
    name: str
    total: int
    solved: int


# ---- problems
class NoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class NoteOut(ORM):
    id: int
    body: str
    created_at: datetime


class CompanyRef(ORM):
    id: int
    name: str


class ProblemBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    leetcode_number: int | None = Field(default=None, ge=1)
    url: str | None = Field(default=None, max_length=500)
    difficulty: Difficulty
    status: Status = "attempted"
    attempts: int = Field(default=1, ge=0, le=1000)
    time_spent_minutes: int = Field(default=0, ge=0, le=10000)
    confidence: int = Field(default=3, ge=1, le=5)
    solution_url: str | None = Field(default=None, max_length=500)
    solution_code: str | None = Field(default=None, max_length=50000)
    topic_ids: list[int] = []
    company_ids: list[int] = []


class ProblemCreate(ProblemBase):
    pass


class ProblemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    leetcode_number: int | None = None
    url: str | None = None
    difficulty: Difficulty | None = None
    status: Status | None = None
    attempts: int | None = Field(default=None, ge=0, le=1000)
    time_spent_minutes: int | None = Field(default=None, ge=0, le=10000)
    confidence: int | None = Field(default=None, ge=1, le=5)
    solution_url: str | None = None
    solution_code: str | None = None
    bookmarked: bool | None = None
    topic_ids: list[int] | None = None
    company_ids: list[int] | None = None


class ProblemOut(ORM):
    id: int
    title: str
    leetcode_number: int | None
    url: str | None
    difficulty: str
    status: str
    attempts: int
    time_spent_minutes: int
    confidence: int
    solution_url: str | None
    solution_code: str | None
    bookmarked: bool
    solved_at: datetime | None
    source: str
    created_at: datetime
    topics: list[TopicOut]
    companies: list[CompanyRef] = []
    notes: list[NoteOut] = []


class Page(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


# ---- goals / revisions
class GoalIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    period: Literal["daily", "weekly", "monthly", "custom"]
    metric: Literal["solved", "attempts"] = "solved"
    target: int = Field(ge=1, le=10000)
    start_date: date | None = None
    end_date: date | None = None


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    target: int | None = Field(default=None, ge=1, le=10000)
    end_date: date | None = None


class RevisionIn(BaseModel):
    problem_id: int
    due_date: date | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    notes: str = Field(default="", max_length=2000)


class RevisionUpdate(BaseModel):
    due_date: date | None = None
    priority: Literal["low", "medium", "high"] | None = None
    status: Literal["pending", "completed", "skipped"] | None = None
    notes: str | None = Field(default=None, max_length=2000)


class RevisionBookmarkIn(BaseModel):
    due_date: date | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    notes: str = ""


# ---- integrations / ai
class LeetCodeConnectIn(BaseModel):
    username: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_\-]+$")


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None


class AIPromptIn(BaseModel):
    focus: str = Field(default="", max_length=500)


class GoalOut(BaseModel):
    id: int
    title: str
    period: str
    metric: str
    target: int
    start_date: date
    end_date: date
    progress: int
    completed: bool
    completed_at: datetime | None
    active: bool


class RevisionOut(BaseModel):
    id: int
    problem_id: int
    problem_title: str
    problem_difficulty: str
    due_date: date
    priority: str
    status: str
    stage: int
    notes: str
    completed_at: datetime | None
    overdue: bool
