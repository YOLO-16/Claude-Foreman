import asyncio
import json
import uuid
from datetime import UTC, datetime

from loguru import logger
from sqlmodel import Session, select

from ..db import engine
from ..models import Decision, Task, TaskStatus
from .events import bus

_waiters: dict[str, asyncio.Event] = {}
_answers: dict[str, str] = {}


def create_decision(
    task_id: int,
    kind: str,
    question: str,
    tool_name: str | None = None,
    payload: dict | None = None,
) -> str:
    did = str(uuid.uuid4())
    with Session(engine) as s:
        s.add(
            Decision(
                id=did,
                task_id=task_id,
                kind=kind,
                tool_name=tool_name,
                question=question[:2000],
                payload=json.dumps(payload or {}, ensure_ascii=False),
            )
        )
        task = s.get(Task, task_id)
        if task and task.status == TaskStatus.running:
            task.status = TaskStatus.needs_decision
            s.add(task)
        s.commit()
    _waiters[did] = asyncio.Event()
    bus.publish(
        task_id,
        {
            "type": "decision",
            "decision_id": did,
            "kind": kind,
            "tool_name": tool_name,
            "question": question[:2000],
            "ts": datetime.now(UTC).isoformat(),
        },
    )
    logger.info("decision {} created for task {}", did, task_id)
    return did


def answer_decision(decision_id: str, answer: str, action: str = "answer") -> bool:
    status = "answered" if action == "answer" else "skipped"
    with Session(engine) as s:
        d = s.get(Decision, decision_id)
        if not d:
            return False
        d.answer = answer
        d.status = status
        d.answered_at = datetime.now(UTC)
        s.add(d)
        s.commit()
        task_id = d.task_id
    _answers[decision_id] = answer
    ev = _waiters.get(decision_id)
    if ev:
        ev.set()
    bus.publish(
        task_id,
        {
            "type": "decision_answered",
            "decision_id": decision_id,
            "answer": answer,
            "ts": datetime.now(UTC).isoformat(),
        },
    )
    return True


async def wait_for_answer(decision_id: str, timeout: float = 55.0) -> str | None:
    ev = _waiters.get(decision_id)
    if not ev:
        return _answers.get(decision_id)
    try:
        await asyncio.wait_for(ev.wait(), timeout=timeout)
    except TimeoutError:
        return None
    return _answers.get(decision_id, "")


def open_decisions(task_id: int) -> list[Decision]:
    with Session(engine) as s:
        return list(
            s.exec(
                select(Decision).where(Decision.task_id == task_id, Decision.status == "open")
            ).all()
        )
