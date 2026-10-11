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
    q = bus.subscribe(task_id)
    try:
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
                msg = await asyncio.wait_for(q.get(), timeout=15.0)
                await websocket.send_text(ws_frame(msg))
            except TimeoutError:
                await websocket.send_text(
                    ws_frame({"type": "ping", "ts": datetime.now(UTC).isoformat()})
                )
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(task_id, q)
