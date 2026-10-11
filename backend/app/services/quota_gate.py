import asyncio
import time


class QuotaGate:
    def __init__(self) -> None:
        self._reset_event = asyncio.Event()
        self._reset_event.set()
        self._reset_at: float | None = None
        self._last_signal: dict | None = None
        self._timer_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    def is_blocked(self) -> bool:
        if self._reset_at is None:
            return False
        return time.time() < self._reset_at

    def remaining(self) -> float:
        if not self.is_blocked():
            return 0.0
        return max(0.0, self._reset_at - time.time())

    async def block(self, reset_at: float | None, pattern: str, raw: str) -> None:
        async with self._lock:
            if reset_at is None:
                reset_at = time.time() + 300
            if self.is_blocked() and self._reset_at and reset_at <= self._reset_at:
                return
            if self._timer_task and not self._timer_task.done():
                self._timer_task.cancel()
            self._reset_at = reset_at
            self._last_signal = {
                "pattern": pattern,
                "reset_at": reset_at,
                "raw": raw[:500],
                "ts": time.time(),
            }
            self._reset_event.clear()
            self._timer_task = asyncio.create_task(
                self._auto_release(max(0.1, reset_at - time.time()))
            )

    def unblock(self) -> None:
        self._reset_at = None
        self._last_signal = None
        self._reset_event.set()
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        self._timer_task = None

    async def wait(self) -> None:
        await self._reset_event.wait()

    async def _auto_release(self, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
            self.unblock()
        except asyncio.CancelledError:
            pass

    def status(self) -> dict:
        return {
            "blocked": self.is_blocked(),
            "reset_at": self._reset_at,
            "remaining_sec": self.remaining(),
            "last_signal": self._last_signal,
        }


gate = QuotaGate()
