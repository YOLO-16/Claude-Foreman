from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlmodel import Session, select

from ..db import get_session
from ..models import Task, TaskStatus
from ..services.reporter import report_markdown

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("")
def list_reports(
    q: str | None = None,
    status: TaskStatus | None = None,
    session_id: str | None = None,
    session: Session = Depends(get_session),
):
    stmt = select(Task).where(Task.report_path.is_not(None))  # type: ignore[attr-defined]
    tasks = list(session.exec(stmt).all())
    if q:
        tasks = [t for t in tasks if q.lower() in t.content.lower()]
    if status:
        tasks = [t for t in tasks if t.status == status]
    if session_id:
        tasks = [t for t in tasks if t.session_id == session_id]
    tasks.sort(key=lambda t: t.completed_at or t.created_at, reverse=True)
    items = [
        {
            "id": t.id,
            "content": t.content[:200],
            "status": t.status,
            "mode": t.mode,
            "session_id": t.session_id,
            "report_path": t.report_path,
            "started_at": t.started_at,
            "completed_at": t.completed_at,
            "tool_call_count": t.tool_call_count,
        }
        for t in tasks
    ]
    return {"items": items, "total": len(items)}


@router.get("/{task_id}")
def get_report(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    md = report_markdown(task_id)
    if md is None:
        raise HTTPException(404, "report not generated")
    return {
        "markdown": md,
        "meta": {
            "id": task.id,
            "status": task.status,
            "session_id": task.session_id,
            "report_path": task.report_path,
        },
    }


@router.get("/{task_id}/export")
def export_report(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    md = report_markdown(task_id)
    if md is None:
        raise HTTPException(404, "report not generated")
    return PlainTextResponse(
        md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="task_{task_id}.md"'},
    )
