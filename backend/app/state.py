from .models import TaskStatus

ALLOWED: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.pending: {TaskStatus.running},
    TaskStatus.running: {
        TaskStatus.completed,
        TaskStatus.failed,
        TaskStatus.needs_decision,
        TaskStatus.pending,
    },
    TaskStatus.needs_decision: {TaskStatus.running},
    TaskStatus.failed: {TaskStatus.pending},
    TaskStatus.completed: {TaskStatus.pending},
}


def can_transition(src: TaskStatus, dst: TaskStatus) -> bool:
    return dst in ALLOWED[src]


def ensure_transition(src: TaskStatus, dst: TaskStatus) -> None:
    if not can_transition(src, dst):
        raise ValueError(f"illegal transition {src.value} -> {dst.value}")
