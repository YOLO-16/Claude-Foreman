import asyncio
import sys
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import Task, TaskMode, TaskStatus
from app.services.executor import run_task
from app.services.quota_gate import gate

FAKE = str(Path(__file__).resolve().parents[2] / "scripts" / "fake_claude.py")


@pytest.fixture()
def db_engine(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/quota.db")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr("app.services.executor.engine", engine)
    monkeypatch.setenv("FOREMAN_CLAUDE_BIN", f"{sys.executable} {FAKE} --quota-after 1 --quota-resets-in 60")
    yield engine
    gate.unblock()


def _make_task(engine, content: str) -> int:
    with Session(engine) as s:
        t = Task(content=content, mode=TaskMode.autopilot, project_path=".")
        s.add(t)
        s.commit()
        s.refresh(t)
        return t.id


def test_rate_limit_marks_failed(db_engine):
    assert not gate.is_blocked()
    tid = _make_task(db_engine, "normal task that hits quota")
    asyncio.run(run_task(tid))
    with Session(db_engine) as s:
        t = s.get(Task, tid)
        assert t.status == TaskStatus.failed
        assert "rate limited" in (t.error or "")
        assert "usage limit reached" in (t.error or "")


def test_rate_limit_blocks_gate(db_engine):
    tid = _make_task(db_engine, "normal task that hits quota")
    asyncio.run(run_task(tid))
    assert gate.is_blocked()
    s = gate.status()
    assert s["blocked"] is True
    assert s["reset_at"] is not None
    assert s["remaining_sec"] > 0
    assert s["last_signal"]["pattern"] == "usage limit reached"


def test_unblock_resets_gate(db_engine):
    tid = _make_task(db_engine, "normal task that hits quota")
    asyncio.run(run_task(tid))
    assert gate.is_blocked()
    gate.unblock()
    assert not gate.is_blocked()
