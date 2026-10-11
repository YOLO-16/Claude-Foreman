from fastapi import APIRouter

from ..services.events import bus
from ..services.quota_gate import gate

router = APIRouter(prefix="/api", tags=["quota"])


@router.get("/quota")
def quota_status() -> dict:
    return gate.status()


@router.post("/quota/unblock")
def quota_unblock() -> dict:
    gate.unblock()
    bus.publish(
        0,
        {
            "type": "quota",
            "blocked": False,
            "reset_at": None,
            "remaining_sec": 0.0,
            "pattern": None,
            "ts": _now_iso(),
        },
    )
    return gate.status()


def _now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()
