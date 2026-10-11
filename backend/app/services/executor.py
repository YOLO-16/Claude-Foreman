import asyncio
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger
from sqlmodel import Session

from ..config import settings
from ..db import engine
from ..models import ExecutionLog, Task, TaskMode, TaskStatus
from ..state import ensure_transition
from .events import bus
from .reporter import write_report
from .stream_parser import StreamParser, detect_rate_limit


def _claude_prefix(claude_bin: str | None) -> list[str]:
    raw = claude_bin or os.environ.get("FOREMAN_CLAUDE_BIN") or settings.claude_bin
    return raw.split() if " " in raw else [raw]


def build_argv(task: Task, claude_bin: str | None = None) -> list[str]:
    args = [
        *_claude_prefix(claude_bin),
        "-p",
        task.content,
        "--output-format",
        "stream-json",
        "--verbose",
        "--session-id",
        task.session_id or str(uuid.uuid4()),
    ]
    if task.mode == TaskMode.autopilot:
        args.append("--dangerously-skip-permissions")
    else:
        args += ["--permission-mode", "acceptEdits"]
        settings_path = _write_interactive_settings(task)
        args += ["--settings", str(settings_path)]
    return args


def build_resume_argv(task: Task, followup: str, claude_bin: str | None = None) -> list[str]:
    return [
        *_claude_prefix(claude_bin),
        "-p",
        followup or "continue",
        "--output-format",
        "stream-json",
        "--verbose",
        "--resume",
        task.session_id or "",
    ]


def _write_interactive_settings(task: Task) -> Path:
    hook_path = Path(__file__).resolve().parents[1] / "hooks" / "pretooluse.py"
    payload = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f'python "{hook_path}"',
                            "timeout": 60,
                        }
                    ],
                }
            ]
        }
    }
    path = settings.tmp_dir / f"settings_{task.id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _log(task_id: int, log_type: str, content: str) -> None:
    content = content[:8192]
    with Session(engine) as s:
        s.add(
            ExecutionLog(
                task_id=task_id,
                log_content=content,
                log_type=log_type,
            )
        )
        s.commit()
    bus.publish(
        task_id,
        {
            "type": "log",
            "task_id": task_id,
            "log_type": log_type,
            "content": content,
            "ts": datetime.now(UTC).isoformat(),
        },
    )


async def run_task(task_id: int) -> None:
    with Session(engine) as s:
        task = s.get(Task, task_id)
        if not task:
            return
        if task.session_id is None:
            task.session_id = str(uuid.uuid4())
        task.status = TaskStatus.running
        task.started_at = datetime.now(UTC)
        task.error = None
        s.add(task)
        s.commit()
        content = task.content
        session_id = task.session_id
        mode = task.mode

    argv = build_argv(Task(id=task_id, content=content, session_id=session_id, mode=mode))
    logger.info("spawn task={} argv={}", task_id, argv)
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=_project_path(task_id),
        )
    except FileNotFoundError as e:
        _finish(task_id, TaskStatus.failed, error=f"claude bin not found: {e}")
        return

    parser = StreamParser()
    timeout = _timeout(task_id)
    try:
        await asyncio.wait_for(
            _pump(task_id, proc, parser),
            timeout=timeout,
        )
    except TimeoutError:
        await _kill(proc)
        _finish(task_id, TaskStatus.failed, error=f"timeout after {timeout}s")
        return

    rc = await proc.wait()
    limit = detect_rate_limit(parser.result_text)
    if limit:
        _finish(task_id, TaskStatus.failed, error=f"rate limited: {limit['pattern']}")
        return
    if rc == 0 and not parser.is_error:
        _finish(task_id, TaskStatus.completed, parser=parser)
    else:
        _finish(task_id, TaskStatus.failed, error=parser.result_text or f"exit {rc}", parser=parser)


async def _pump(task_id: int, proc: asyncio.subprocess.Process, parser: StreamParser) -> None:
    assert proc.stdout and proc.stderr
    async for raw in proc.stdout:
        line = raw.decode("utf-8", errors="replace")
        for ev in parser.feed(line):
            _log(task_id, ev.log_type, ev.content)
    async for raw in proc.stderr:
        line = raw.decode("utf-8", errors="replace").rstrip()
        if line:
            _log(task_id, "stderr", line[:8192])


async def _kill(proc: asyncio.subprocess.Process) -> None:
    try:
        proc.terminate()
        await asyncio.wait_for(proc.wait(), timeout=3)
    except (TimeoutError, ProcessLookupError):
        try:
            proc.kill()
        except ProcessLookupError:
            pass


def _finish(
    task_id: int,
    status: TaskStatus,
    error: str | None = None,
    parser: StreamParser | None = None,
) -> None:
    with Session(engine) as s:
        task = s.get(Task, task_id)
        if not task:
            return
        try:
            ensure_transition(task.status, status)
        except ValueError as e:
            logger.warning("transition skip: {}", e)
        task.status = status
        task.completed_at = datetime.now(UTC)
        task.error = error
        if parser:
            task.tool_call_count = parser.tool_call_count
            if parser.session_id:
                task.session_id = parser.session_id
        s.add(task)
        s.commit()
    if parser and parser.result_text:
        _log(task_id, "result", parser.result_text[:8192])
    try:
        write_report(task_id)
    except Exception as e:
        logger.warning("report write failed for {}: {}", task_id, e)
    bus.publish(
        task_id,
        {
            "type": "done",
            "task_id": task_id,
            "status": status.value if hasattr(status, "value") else str(status),
            "ts": datetime.now(UTC).isoformat(),
        },
    )


def _mode(task_id: int) -> TaskMode:
    with Session(engine) as s:
        task = s.get(Task, task_id)
        return task.mode if task else TaskMode.autopilot


def _timeout(task_id: int) -> int:
    with Session(engine) as s:
        task = s.get(Task, task_id)
        return task.timeout_seconds if task else settings.default_timeout_seconds


def _project_path(task_id: int) -> str:
    with Session(engine) as s:
        task = s.get(Task, task_id)
        if task and task.project_path:
            p = Path(task.project_path)
            if p.exists():
                return str(p)
        return str(Path.cwd())
