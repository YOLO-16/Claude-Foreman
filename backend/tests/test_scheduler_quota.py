import asyncio
import time
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import Task, TaskMode, TaskStatus
from app.services.quota_gate import gate
from app.services.scheduler import _loop


@pytest.fixture()
def engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/sched.db")
    SQLModel.metadata.create_all(engine)
    return engine


def _seed(engine, n: int) -> list[int]:
    ids = []
    with Session(engine) as s:
        for i in range(n):
            t = Task(content=f"task {i}", mode=TaskMode.autopilot, project_path=".")
            s.add(t)
            s.commit()
            s.refresh(t)
            ids.append(t.id)
    return ids


def _count_status(engine, status) -> int:
    from sqlmodel import select

    with Session(engine) as s:
        return len(s.exec(select(Task).where(Task.status == status)).all())


@pytest.mark.asyncio
async def test_scheduler_waits_when_quota_blocked(engine, monkeypatch):
    import app.services.executor as exec_mod
    import app.services.scheduler as sched

    monkeypatch.setattr(sched, "engine", engine)
    monkeypatch.setattr(exec_mod, "engine", engine)
    monkeypatch.setattr(sched, "_active", True)

    _seed(engine, 2)

    gate.unblock()

    async def fake_run_task(task_id):
        from datetime import UTC, datetime

        with Session(engine) as s:
            t = s.get(Task, task_id)
            if t:
                t.status = TaskStatus.running
                t.started_at = datetime.now(UTC)
                s.add(t)
                s.commit()
        await asyncio.Event().wait()

    monkeypatch.setattr(sched, "run_task", fake_run_task)

    await gate.block(time.time() + 3.0, "test", "raw")
    assert gate.is_blocked()

    worker = asyncio.create_task(_loop())
    try:
        await asyncio.sleep(0.5)
        with Session(engine) as s:
            from sqlmodel import select

            running = s.exec(
                select(Task).where(Task.status == TaskStatus.running)
            ).all()
            assert len(running) == 0
            pending = s.exec(
                select(Task).where(Task.status == TaskStatus.pending)
            ).all()
            assert len(pending) == 2
    finally:
        gate.unblock()
        monkeypatch.setattr(sched, "_active", False)
        await asyncio.sleep(0.1)
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass
