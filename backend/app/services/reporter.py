from pathlib import Path

from sqlmodel import Session, select

from ..config import settings
from ..db import engine
from ..models import Decision, ExecutionLog, Task


def write_report(task_id: int) -> str | None:
    with Session(engine) as s:
        task = s.get(Task, task_id)
        if not task:
            return None
        logs = s.exec(
            select(ExecutionLog).where(ExecutionLog.task_id == task_id).order_by(ExecutionLog.id)
        ).all()
        decisions = s.exec(
            select(Decision).where(Decision.task_id == task_id).order_by(Decision.created_at)
        ).all()

    lines = [
        f"# 任务报告 #{task.id}",
        "",
        f"- 状态: **{task.status}**",
        f"- 模式: {task.mode}",
        f"- Session: `{task.session_id or '-'}`",
        f"- 项目: `{task.project_path}`",
        f"- 开始: {task.started_at or '-'}",
        f"- 结束: {task.completed_at or '-'}",
        f"- 工具调用: {task.tool_call_count}",
        f"- 重试: {task.retry_count}/{task.max_retries}",
    ]
    if task.error:
        lines += ["", f"> 错误: {task.error[:500]}"]

    lines += ["", "## 任务内容", "", task.content]

    result_logs = [lg for lg in logs if lg.log_type == "result"]
    if result_logs:
        lines += ["", "## 执行摘要", "", result_logs[-1].log_content]

    if decisions:
        lines += ["", "## 决策点", ""]
        for d in decisions:
            lines.append(f"- **{d.kind}** [{d.status}] {d.question[:200]}")
            if d.answer:
                lines.append(f"  - 回答: {d.answer}")

    marker_logs = [lg for lg in logs if "【需人工决策】" in lg.log_content]
    if marker_logs:
        lines += ["", "## 决策标记", ""]
        for lg in marker_logs[:20]:
            lines.append(f"- {lg.log_content[:300]}")

    tool_logs = [lg for lg in logs if lg.log_type == "tool_call"]
    if tool_logs:
        lines += ["", "## 工具调用摘要", ""]
        for lg in tool_logs[:50]:
            lines.append(f"- {lg.log_content[:200]}")

    path = settings.reports_dir / f"task_{task.id}_{task.session_id or 'nosession'}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    with Session(engine) as s:
        t = s.get(Task, task_id)
        if t:
            t.report_path = str(path)
            s.add(t)
            s.commit()
    return str(path)


def report_markdown(task_id: int) -> str | None:
    with Session(engine) as s:
        task = s.get(Task, task_id)
        if not task or not task.report_path:
            return None
    p = Path(task.report_path)
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")
