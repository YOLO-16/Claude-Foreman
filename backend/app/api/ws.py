import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from ..db import engine
from ..models import ExecutionLog
from ..services.events import bus, ws_frame

router = APIRouter()


@router.websocket("/ws/tasks/{task_id}/logs")
async def task_logs_ws(websocket: WebSocket, task_id: int):
    await websocket.accept()
    task_q = bus.subscribe(task_id)
    global_q = bus.subscribe(0) if task_id != 0 else None
    try:
        if task_id != 0:
            with Session(engine) as s:
                logs = s.exec(
                    select(ExecutionLog)
                    .where(ExecutionLog.task_id == task_id)
                    .order_by(ExecutionLog.id)
                ).all()
                for log in logs[-200:]:
                    await websocket.send_text(
                        ws_frame(
                            {
                                "type": "log",
                                "task_id": task_id,
                                "log_type": log.log_type,
                                "content": log.log_content,
                                "ts": log.timestamp.isoformat(),
                            }
                        )
                    )
        while True:
            try:
                msg = await asyncio.wait_for(_next_msg(task_q, global_q), timeout=15.0)
                await websocket.send_text(ws_frame(msg))
            except TimeoutError:
                await websocket.send_text(
                    ws_frame({"type": "ping", "ts": datetime.now(UTC).isoformat()})
                )
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(task_id, task_q)
        if global_q is not None:
            bus.unsubscribe(0, global_q)


async def _next_msg(task_q: asyncio.Queue, global_q: asyncio.Queue | None) -> dict:
    queues = [task_q] if global_q is None else [task_q, global_q]
    get_tasks = [asyncio.create_task(q.get()) for q in queues]
    done, _ = await asyncio.wait(get_tasks, return_when=asyncio.FIRST_COMPLETED)
    for t in get_tasks:
        if not t.done():
            t.cancel()
    return done.pop().result()
