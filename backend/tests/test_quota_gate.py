import asyncio
import time

import pytest

from app.services.quota_gate import QuotaGate


@pytest.fixture()
def gate():
    return QuotaGate()


async def test_block_sets_state_and_event(gate: QuotaGate):
    assert not gate.is_blocked()
    await gate.block(time.time() + 10, "usage limit reached", "raw msg")
    assert gate.is_blocked()
    assert gate.remaining() > 0
    assert gate.remaining() <= 10


async def test_unblock_clears_state(gate: QuotaGate):
    await gate.block(time.time() + 10, "x", "raw")
    gate.unblock()
    assert not gate.is_blocked()
    assert gate.remaining() == 0
    assert gate.status()["last_signal"] is None


async def test_wait_returns_when_unblocked(gate: QuotaGate):
    await gate.block(time.time() + 0.5, "x", "raw")
    await asyncio.wait_for(gate.wait(), timeout=2)
    assert not gate.is_blocked()


async def test_block_with_no_reset_uses_default(gate: QuotaGate):
    await gate.block(None, "x", "raw")
    assert gate.is_blocked()
    assert 200 <= gate.remaining() <= 400


async def test_block_does_not_downgrade(gate: QuotaGate):
    later = time.time() + 3600
    earlier = time.time() + 60
    await gate.block(later, "later", "raw")
    await gate.block(earlier, "earlier", "raw")
    assert gate._reset_at == later


async def test_status_shape(gate: QuotaGate):
    await gate.block(time.time() + 30, "usage limit reached", "raw text")
    s = gate.status()
    assert s["blocked"] is True
    assert s["reset_at"] is not None
    assert s["remaining_sec"] > 0
    assert s["last_signal"]["pattern"] == "usage limit reached"
    assert s["last_signal"]["raw"] == "raw text"


async def test_auto_release_after_delay():
    g = QuotaGate()
    await g.block(time.time() + 0.2, "x", "raw")
    assert g.is_blocked()
    await asyncio.sleep(0.5)
    assert not g.is_blocked()
