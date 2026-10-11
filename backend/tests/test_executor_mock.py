import asyncio
import sys
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import Task, TaskMode, TaskStatus
from app.services.executor import run_task

FAKE = str(Path(__file__).resolve().parents[2] / "scripts" / "fake_claude.py")


@pytest.fixture()
def db_engine(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/exec.db")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr("app.services.executor.engine", engine)
    monkeypatch.setenv("FOREMAN_CLAUDE_BIN", f"{sys.executable} {FAKE}")
    return engine


def _make_task(engine, content: str, **kw) -> int:
    with Session(engine) as s:
        t = Task(content=content, mode=TaskMode.autopilot, project_path=".", **kw)
        s.add(t)
        s.commit()
        s.refresh(t)
        return t.id


def test_run_success(db_engine):
    tid = _make_task(db_engine, "create hello file")
    asyncio.run(run_task(tid))
    with Session(db_engine) as s:
        t = s.get(Task, tid)
        assert t.status == TaskStatus.completed
        assert t.session_id is not None
        assert t.tool_call_count >= 1


def test_run_failure(db_engine):
    tid = _make_task(db_engine, "please FAIL now")
    asyncio.run(run_task(tid))
    with Session(db_engine) as s:
        t = s.get(Task, tid)
        assert t.status == TaskStatus.failed
        assert t.error
