import json
import subprocess
import sys
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.models import Decision, Task, TaskStatus
from app.services.decision_hub import answer_decision, create_decision, open_decisions

HOOK = Path(__file__).resolve().parents[1] / "app" / "hooks" / "pretooluse.py"


def test_create_and_answer(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/d.db")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr("app.services.decision_hub.engine", engine)

    with Session(engine) as s:
        t = Task(content="x", status=TaskStatus.running)
        s.add(t)
        s.commit()
        s.refresh(t)
        tid = t.id

    did = create_decision(tid, "ask_user", "选哪个？", tool_name="AskUserQuestion")
    assert open_decisions(tid)

    with Session(engine) as s:
        assert s.get(Task, tid).status == TaskStatus.needs_decision

    assert answer_decision(did, "A")
    assert not open_decisions(tid)
    with Session(engine) as s:
        d = s.get(Decision, did)
        assert d.status == "answered"
        assert d.answer == "A"


def test_hook_denies_on_bad_input():
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input="not json",
        capture_output=True,
        text=True,
    )
    out = json.loads(proc.stdout)
    assert out["permissionDecision"] == "deny"


def test_hook_allows_read(tmp_path, monkeypatch):
    monkeypatch.setenv("FOREMAN_TASK_ID", "1")
    monkeypatch.setenv("FOREMAN_TMP", str(tmp_path))
    monkeypatch.setenv("FOREMAN_INTERACTIVE", "0")
    payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "a.py"}})
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
    )
    out = json.loads(proc.stdout)
    assert out["permissionDecision"] == "allow"


def test_hook_defers_write_in_interactive(tmp_path, monkeypatch):
    monkeypatch.setenv("FOREMAN_TASK_ID", "1")
    monkeypatch.setenv("FOREMAN_TMP", str(tmp_path))
    monkeypatch.setenv("FOREMAN_INTERACTIVE", "1")
    monkeypatch.setenv("FOREMAN_DECISION_URL", "http://127.0.0.1:1")
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "a.py"}})
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
    )
    out = json.loads(proc.stdout)
    assert out["permissionDecision"] == "defer"
