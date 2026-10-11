import asyncio
import json
from collections import defaultdict
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[int, set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, task_id: int) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subs[task_id].add(q)
        return q

    def unsubscribe(self, task_id: int, q: asyncio.Queue) -> None:
        self._subs[task_id].discard(q)
        if not self._subs[task_id]:
            self._subs.pop(task_id, None)

    def publish(self, task_id: int, message: dict[str, Any]) -> None:
        for q in list(self._subs.get(task_id, ())):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                pass


bus = EventBus()


def ws_frame(message: dict[str, Any]) -> str:
    return json.dumps(message, ensure_ascii=False)
