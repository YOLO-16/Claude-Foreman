from sqlmodel import Session, SQLModel, create_engine

from app.models import Decision, ExecutionLog, Task, TaskStatus
from app.services.reporter import report_markdown, write_report


def test_write_report(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/r.db")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr("app.services.reporter.engine", engine)
    monkeypatch.setattr("app.services.reporter.settings.reports_dir", tmp_path / "reports")
    (tmp_path / "reports").mkdir()

    with Session(engine) as s:
        t = Task(content="补全单测", status=TaskStatus.completed, session_id="abc")
        s.add(t)
        s.commit()
        s.refresh(t)
        tid = t.id
        s.add(ExecutionLog(task_id=tid, log_content="Bash: npm test", log_type="tool_call"))
        s.add(ExecutionLog(task_id=tid, log_content="done ok", log_type="result"))
        s.add(
            Decision(
                id="d1",
                task_id=tid,
                kind="ask_user",
                question="选哪个？",
                answer="A",
                status="answered",
            )
        )
        s.commit()

    path = write_report(tid)
    assert path is not None
    md = report_markdown(tid)
    assert md is not None
    assert "补全单测" in md
    assert "选哪个？" in md
    assert "Bash: npm test" in md
