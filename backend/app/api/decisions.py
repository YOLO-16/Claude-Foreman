from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ..db import get_session
from ..models import Decision, Task, TaskStatus
from ..schemas import DecisionRespond
from ..services import decision_hub
from ..services.executor import run_task

router = APIRouter(prefix="/api", tags=["decisions"])


class DecisionCreate(BaseModel):
    task_id: int
    kind: str = "ask_user"
    question: str
    tool_name: str | None = None
    payload: dict = {}


@router.post("/internal/decisions")
def create_decision(body: DecisionCreate):
    did = decision_hub.create_decision(
        task_id=body.task_id,
        kind=body.kind,
        question=body.question,
        tool_name=body.tool_name,
        payload=body.payload,
    )
    return {"id": did}


@router.get("/internal/decisions/{decision_id}/wait")
async def wait_decision(decision_id: str, session: Session = Depends(get_session)):
    d = session.get(Decision, decision_id)
    if not d:
        raise HTTPException(404, "decision not found")
    if d.status == "open":
        answer = await decision_hub.wait_for_answer(decision_id, timeout=50.0)
        if answer is not None:
            session.refresh(d)
            d = session.get(Decision, decision_id)
    else:
        answer = d.answer or ""
    return {
        "status": d.status if d else "open",
        "answer": (d.answer if d else answer) or answer or "",
    }


@router.post("/tasks/{task_id}/decisions/{decision_id}/respond")
async def respond_decision(
    task_id: int,
    decision_id: str,
    body: DecisionRespond,
    session: Session = Depends(get_session),
):
    d = session.get(Decision, decision_id)
    if not d or d.task_id != task_id:
        raise HTTPException(404, "decision not found")
    if d.status != "open":
        raise HTTPException(409, "already answered")
    decision_hub.answer_decision(decision_id, body.answer, body.action)

    open_left = decision_hub.open_decisions(task_id)
    if not open_left:
        task = session.get(Task, task_id)
        if task and task.status == TaskStatus.needs_decision:
            task.status = TaskStatus.pending
            session.add(task)
            session.commit()
            import asyncio

            asyncio.create_task(run_task(task_id))
    return {"ok": True}
