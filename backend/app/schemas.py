from datetime import datetime

from pydantic import BaseModel, Field

from .models import TaskMode, TaskStatus


class DecisionOut(BaseModel):
    id: str
    kind: str
    tool_name: str | None = None
    question: str
    status: str
    created_at: datetime


class TaskCreate(BaseModel):
    content: str = Field(min_length=1)
    priority: int = Field(default=5, ge=1, le=9)
    tags: list[str] = Field(default_factory=list)
    mode: TaskMode = TaskMode.autopilot
    project_path: str = "."
    timeout_seconds: int = Field(default=1800, ge=1)
    tool_budget: int = Field(default=80, ge=1)
    max_retries: int = Field(default=0, ge=0)


class TaskUpdate(BaseModel):
    content: str | None = None
    priority: int | None = Field(default=None, ge=1, le=9)
    tags: list[str] | None = None
    mode: TaskMode | None = None
    project_path: str | None = None
    timeout_seconds: int | None = Field(default=None, ge=1)
    tool_budget: int | None = Field(default=None, ge=1)
    max_retries: int | None = Field(default=None, ge=0)


class TaskOut(BaseModel):
    id: int
    content: str
    priority: int
    tags: list[str]
    status: TaskStatus
    mode: TaskMode
    session_id: str | None = None
    report_path: str | None = None
    project_path: str
    error: str | None = None
    tool_call_count: int
    retry_count: int
    max_retries: int
    timeout_seconds: int
    tool_budget: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    decisions: list[DecisionOut] = Field(default_factory=list)


class BatchImport(BaseModel):
    text: str = Field(min_length=1)
    mode: TaskMode = TaskMode.autopilot
    project_path: str = "."
    tags: list[str] = Field(default_factory=list)
    priority: int = Field(default=5, ge=1, le=9)


class LogOut(BaseModel):
    id: int
    task_id: int
    log_content: str
    log_type: str
    timestamp: datetime


class DecisionRespond(BaseModel):
    answer: str = ""
    action: str = Field(default="answer", pattern="^(answer|skip)$")


class FileChange(BaseModel):
    path: str
    status: str
