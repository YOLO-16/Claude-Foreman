import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import Decision, Task, TaskStatus
from ..schemas import BatchImport, LogOut, TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _tags_loads(s: str) -> list[str]:
    try:
        return json.loads(s)
    except Exception:
        return []


def _task_out(task: Task, decisions: list[Decision]) -> TaskOut:
    return TaskOut(
        id=task.id,
        content=task.content,
        priority=task.priority,
        tags=_tags_loads(task.tags),
        status=task.status,
        mode=task.mode,
        session_id=task.session_id,
        report_path=task.report_path,
        project_path=task.project_path,
        error=task.error,
        tool_call_count=task.tool_call_count,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        timeout_seconds=task.timeout_seconds,
        tool_budget=task.tool_budget,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        decisions=[
            {
                "id": d.id,
                "kind": d.kind,
                "tool_name": d.tool_name,
                "question": d.question,
                "status": d.status,
                "created_at": d.created_at,
            }
            for d in decisions
        ],
    )


def _get_task(session: Session, task_id: int) -> Task:
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    return task


def _decisions_of(session: Session, task_id: int) -> list[Decision]:
    return list(session.exec(select(Decision).where(Decision.task_id == task_id)).all())


@router.get("", response_model=dict)
def list_tasks(
    status: TaskStatus | None = None,
    tag: str | None = None,
    q: str | None = None,
    sort: str = Query(default="priority", pattern="^(priority|created_at)$"),
    session: Session = Depends(get_session),
):
    stmt = select(Task)
    if status:
        stmt = stmt.where(Task.status == status)
    if q:
        stmt = stmt.where(Task.content.contains(q))
    tasks = list(session.exec(stmt).all())
    if tag:
        tasks = [t for t in tasks if tag in _tags_loads(t.tags)]
    if sort == "priority":
        tasks.sort(key=lambda t: (-t.priority, t.created_at))
    else:
        tasks.sort(key=lambda t: t.created_at, reverse=True)
    items = [_task_out(t, _decisions_of(session, t.id)) for t in tasks]
    return {"items": items, "total": len(items)}


@router.post("", response_model=TaskOut)
def create_task(body: TaskCreate, session: Session = Depends(get_session)):
    task = Task(
        content=body.content,
        priority=body.priority,
        tags=json.dumps(body.tags, ensure_ascii=False),
        mode=body.mode,
        project_path=body.project_path,
        timeout_seconds=body.timeout_seconds,
        tool_budget=body.tool_budget,
        max_retries=body.max_retries,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return _task_out(task, [])


@router.post("/batch", response_model=dict)
def batch_import(body: BatchImport, session: Session = Depends(get_session)):
    created = []
    for line in body.text.splitlines():
        content = line.strip()
        if not content:
            continue
        task = Task(
            content=content,
            priority=body.priority,
            tags=json.dumps(body.tags, ensure_ascii=False),
            mode=body.mode,
            project_path=body.project_path,
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        created.append(_task_out(task, []))
    return {"created": created}


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, session: Session = Depends(get_session)):
    task = _get_task(session, task_id)
    return _task_out(task, _decisions_of(session, task_id))


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, body: TaskUpdate, session: Session = Depends(get_session)):
    task = _get_task(session, task_id)
    if task.status == TaskStatus.running:
        raise HTTPException(409, "cannot edit running task")
    data = body.model_dump(exclude_unset=True)
    if "tags" in data:
        task.tags = json.dumps(data.pop("tags"), ensure_ascii=False)
    for k, v in data.items():
        setattr(task, k, v)
    session.add(task)
    session.commit()
    session.refresh(task)
    return _task_out(task, _decisions_of(session, task_id))


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, session: Session = Depends(get_session)):
    task = _get_task(session, task_id)
    if task.status == TaskStatus.running:
        raise HTTPException(409, "cannot delete running task")
    for d in _decisions_of(session, task_id):
        session.delete(d)
    session.delete(task)
    session.commit()


@router.get("/{task_id}/logs", response_model=dict)
def get_logs(
    task_id: int,
    after_id: int = 0,
    session: Session = Depends(get_session),
):
    from ..models import ExecutionLog

    _get_task(session, task_id)
    logs = list(
        session.exec(
            select(ExecutionLog)
            .where(ExecutionLog.task_id == task_id, ExecutionLog.id > after_id)
            .order_by(ExecutionLog.id)
        ).all()
    )
    items = [
        LogOut(
            id=log.id,
            task_id=log.task_id,
            log_content=log.log_content,
            log_type=log.log_type,
            timestamp=log.timestamp,
        )
        for log in logs
    ]
    return {"items": items}
