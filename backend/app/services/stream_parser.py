import json
import re
from dataclasses import dataclass, field

DECISION_MARKERS = ("【需人工决策】", "DECISION_REQUIRED")
MAX_LOG_LEN = 8 * 1024


@dataclass
class StreamEvent:
    type: str
    log_type: str
    content: str
    extra: dict = field(default_factory=dict)


def _truncate(s: str) -> str:
    return s if len(s) <= MAX_LOG_LEN else s[:MAX_LOG_LEN] + "...[truncated]"


class StreamParser:
    def __init__(self) -> None:
        self.session_id: str | None = None
        self.tool_call_count = 0
        self.num_turns = 0
        self.cost_usd: float | None = None
        self.result_text = ""
        self.is_error = False
        self.plain_mode = False
        self._rate_limit_emitted = False
        self.rate_limit_signal: dict | None = None

    def feed(self, line: str) -> list[StreamEvent]:
        line = line.rstrip("\n\r")
        if not line:
            return []
        if self.plain_mode:
            return self._plain(line)
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            self.plain_mode = True
            return self._plain(line)
        if not isinstance(data, dict):
            self.plain_mode = True
            return self._plain(line)
        return self._handle(data, line)

    def _plain(self, line: str) -> list[StreamEvent]:
        events = [StreamEvent("log", "stdout", _truncate(line))]
        events.extend(self._scan_decision(line, "text_marker"))
        events.extend(self._scan_rate_limit(line))
        return events

    def _handle(self, data: dict, raw: str) -> list[StreamEvent]:
        t = data.get("type", "")
        if t == "system" and data.get("subtype") == "init":
            self.session_id = data.get("session_id") or self.session_id
            model = data.get("model", "")
            return [StreamEvent("log", "system", f"init model={model} session={self.session_id}")]
        if t == "assistant":
            return self._assistant(data)
        if t == "user":
            return self._user(data)
        if t == "result":
            return self._result(data)
        return [StreamEvent("log", "stdout", _truncate(raw))]

    def _assistant(self, data: dict) -> list[StreamEvent]:
        events: list[StreamEvent] = []
        msg = data.get("message") or {}
        content = msg.get("content")
        if isinstance(content, str):
            events.append(StreamEvent("log", "stdout", _truncate(content)))
            events.extend(self._scan_decision(content))
            events.extend(self._scan_rate_limit(content))
            return events
        if not isinstance(content, list):
            return events
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                text = block.get("text", "")
                events.append(StreamEvent("log", "stdout", _truncate(text)))
                events.extend(self._scan_decision(text))
                events.extend(self._scan_rate_limit(text))
            elif btype == "tool_use":
                self.tool_call_count += 1
                name = block.get("name", "?")
                inp = json.dumps(block.get("input", {}), ensure_ascii=False)
                events.append(
                    StreamEvent(
                        "log",
                        "tool_call",
                        _truncate(f"{name}: {inp}"),
                        {"tool_name": name, "tool_id": block.get("id")},
                    )
                )
                if name == "AskUserQuestion":
                    events.append(
                        StreamEvent(
                            "decision",
                            "decision",
                            _truncate(block.get("input", {}).get("question", "")),
                            {
                                "kind": "ask_user",
                                "tool_name": name,
                                "payload": block.get("input", {}),
                            },
                        )
                    )
        return events

    def _user(self, data: dict) -> list[StreamEvent]:
        events: list[StreamEvent] = []
        msg = data.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            return events
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                body = block.get("content", "")
                if not isinstance(body, str):
                    body = json.dumps(body, ensure_ascii=False)
                events.append(StreamEvent("log", "tool_call", _truncate(f"result: {body}")))
        return events

    def _result(self, data: dict) -> list[StreamEvent]:
        self.num_turns = data.get("num_turns") or self.num_turns
        self.cost_usd = data.get("total_cost_usd")
        self.result_text = data.get("result") or ""
        self.is_error = bool(data.get("is_error"))
        if data.get("session_id"):
            self.session_id = data["session_id"]
        kind = "failed" if self.is_error else "completed"
        summary = (
            f"result {kind} turns={self.num_turns} cost={self.cost_usd} "
            f"tools={self.tool_call_count}"
        )
        events = [StreamEvent("log", "result", summary)]
        events.extend(self._scan_decision(self.result_text))
        events.extend(self._scan_rate_limit(self.result_text))
        return events

    def _scan_decision(self, text: str, kind: str = "text_marker") -> list[StreamEvent]:
        for marker in DECISION_MARKERS:
            if marker in text:
                return [
                    StreamEvent(
                        "decision",
                        "decision",
                        _truncate(text),
                        {"kind": kind, "tool_name": None, "payload": {}},
                    )
                ]
        return []

    def _scan_rate_limit(self, text: str) -> list[StreamEvent]:
        if self._rate_limit_emitted:
            return []
        limit = detect_rate_limit(text)
        if not limit:
            return []
        self._rate_limit_emitted = True
        self.rate_limit_signal = {"pattern": limit["pattern"], "reset_at": limit["reset_at"]}
        return [
            StreamEvent(
                "rate_limit",
                "rate_limit",
                _truncate(limit["raw"]),
                {"pattern": limit["pattern"], "reset_at": limit["reset_at"]},
            )
        ]


RATE_LIMIT_PATTERNS = [
    r"usage limit reached",
    r"exceeded your rate limit",
    r"reached your usage limit",
    r"hit your session limit",
    r"rate_limit_error",
    r"your limit will reset",
    r"try again in \d+",
    r"\b429\b",
]

_RESET_TS = re.compile(r"(\d{10,13})")
_RESET_IN = re.compile(
    r"(?:try again in|resets? in)\s+(\d+)\s*(second|minute|hour|sec|min|hr)", re.I
)


def detect_rate_limit(text: str) -> dict | None:
    if not text:
        return None
    low = text[:2048].lower()
    for pat in RATE_LIMIT_PATTERNS:
        if re.search(pat, low):
            return {"pattern": pat, "reset_at": _extract_reset(text), "raw": text[:500]}
    return None


def _extract_reset(text: str) -> float | None:
    import time

    m = _RESET_TS.search(text)
    if m:
        ts = float(m.group(1))
        if ts > 1e12:
            ts /= 1000
        if 0 < ts - time.time() < 24 * 3600:
            return ts
    m = _RESET_IN.search(text)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()
        mult = 1 if unit.startswith("s") else 60 if unit.startswith("m") else 3600
        return time.time() + n * mult
    return None
