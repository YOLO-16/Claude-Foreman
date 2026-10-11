from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class TaskStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    needs_decision = "needs_decision"


class TaskMode(StrEnum):
    interactive = "interactive"
    autopilot = "autopilot"


class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: int | None = Field(default=None, primary_key=True)
    content: str
    priority: int = 5
    tags: str = "[]"
    status: TaskStatus = TaskStatus.pending
    mode: TaskMode = TaskMode.autopilot
    session_id: str | None = None
    report_path: str | None = None
    project_path: str = "."
    error: str | None = None
    tool_call_count: int = 0
    retry_count: int = 0
    max_retries: int = 0
    timeout_seconds: int = 1800
    tool_budget: int = 80
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ExecutionLog(SQLModel, table=True):
    __tablename__ = "execution_logs"

    id: int | None = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="tasks.id", index=True)
    log_content: str
    log_type: str
    timestamp: datetime = Field(default_factory=utcnow)


class Decision(SQLModel, table=True):
    __tablename__ = "decisions"

    id: str = Field(primary_key=True)
    task_id: int = Field(foreign_key="tasks.id", index=True)
    kind: str
    tool_name: str | None = None
    question: str
    payload: str = "{}"
    answer: str | None = None
    status: str = "open"
    created_at: datetime = Field(default_factory=utcnow)
    answered_at: datetime | None = None
