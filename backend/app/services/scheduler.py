import asyncio

from loguru import logger
from sqlmodel import Session, select

from ..db import engine
from ..models import Task, TaskStatus
from .executor import run_task

_active = False
_worker: asyncio.Task | None = None


def is_active() -> bool:
    return _active


def start_queue() -> None:
    global _active, _worker
    if _active:
        return
    _active = True
    _worker = asyncio.create_task(_loop())
    logger.info("queue started")


def stop_queue() -> None:
    global _active
    _active = False
    logger.info("queue stopped")


async def _loop() -> None:
    while _active:
        task_id = _next_pending()
        if task_id is None:
            await asyncio.sleep(1.0)
            continue
        logger.info("scheduler picked task={}", task_id)
        try:
            await run_task(task_id)
        except Exception as e:
            logger.exception("task {} crashed: {}", task_id, e)
            _mark_failed(task_id, str(e))
        await asyncio.sleep(0.1)


def _next_pending() -> int | None:
    with Session(engine) as s:
        running = s.exec(select(Task).where(Task.status == TaskStatus.running)).first()
        if running:
            return None
        blocked = s.exec(select(Task).where(Task.status == TaskStatus.needs_decision)).first()
        if blocked:
            return None
        task = s.exec(
            select(Task)
            .where(Task.status == TaskStatus.pending)
            .order_by(Task.priority.desc(), Task.created_at)
        ).first()
        return task.id if task else None


def _mark_failed(task_id: int, error: str) -> None:
    from datetime import UTC, datetime

    with Session(engine) as s:
        task = s.get(Task, task_id)
        if not task:
            return
        task.status = TaskStatus.failed
        task.error = error[:2000]
        task.completed_at = datetime.now(UTC)
        s.add(task)
        s.commit()
