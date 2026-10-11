import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Task, TaskStatus
from ..services.executor import run_task
from ..services.scheduler import is_active, start_queue, stop_queue

router = APIRouter(prefix="/api", tags=["queue"])


@router.get("/queue")
def queue_status(session: Session = Depends(get_session)):
    running = session.exec(select(Task).where(Task.status == TaskStatus.running)).first()
    pending = list(
        session.exec(
            select(Task)
            .where(Task.status == TaskStatus.pending)
            .order_by(Task.priority.desc(), Task.created_at)
        ).all()
    )
    return {
        "running_id": running.id if running else None,
        "pending": [t.id for t in pending],
        "is_active": is_active(),
    }


@router.post("/queue/start")
def queue_start():
    start_queue()
    return {"ok": True}


@router.post("/queue/stop")
def queue_stop():
    stop_queue()
    return {"ok": True}


@router.post("/tasks/{task_id}/start", response_model=dict)
def start_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    if task.status not in (TaskStatus.pending, TaskStatus.failed):
        raise HTTPException(409, f"cannot start from {task.status}")
    task.status = TaskStatus.pending
    if task.status == TaskStatus.failed:
        task.retry_count += 1
    session.add(task)
    session.commit()
    asyncio.create_task(run_task(task_id))
    return {"ok": True, "id": task_id}


@router.post("/tasks/{task_id}/stop", response_model=dict)
def stop_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    if task.status != TaskStatus.running:
        raise HTTPException(409, "not running")
    task.status = TaskStatus.pending
    task.error = "stopped by user"
    session.add(task)
    session.commit()
    return {"ok": True}


@router.post("/tasks/{task_id}/retry", response_model=dict)
def retry_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    if task.status != TaskStatus.failed:
        raise HTTPException(409, "only failed tasks can retry")
    if task.retry_count >= task.max_retries and task.max_retries > 0:
        raise HTTPException(409, "retry budget exhausted")
    task.status = TaskStatus.pending
    task.retry_count += 1
    task.error = None
    session.add(task)
    session.commit()
    asyncio.create_task(run_task(task_id))
    return {"ok": True}
