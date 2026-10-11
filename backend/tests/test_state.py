import pytest

from app.models import TaskStatus
from app.state import can_transition, ensure_transition


def test_pending_to_running():
    assert can_transition(TaskStatus.pending, TaskStatus.running)


def test_running_to_terminal():
    assert can_transition(TaskStatus.running, TaskStatus.completed)
    assert can_transition(TaskStatus.running, TaskStatus.failed)
    assert can_transition(TaskStatus.running, TaskStatus.needs_decision)


def test_illegal_transition():
    assert not can_transition(TaskStatus.completed, TaskStatus.running)
    assert not can_transition(TaskStatus.pending, TaskStatus.completed)
    with pytest.raises(ValueError):
        ensure_transition(TaskStatus.pending, TaskStatus.failed)


def test_needs_decision_resume():
    assert can_transition(TaskStatus.needs_decision, TaskStatus.running)
    assert can_transition(TaskStatus.failed, TaskStatus.pending)
