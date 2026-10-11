"""PreToolUse hook for interactive mode.

stdin: hook event JSON. stdout: hook result JSON (protocol channel).
All logs must go to stderr.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _log(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def _post(base: str, path: str, payload: dict) -> dict | None:
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        _log(f"post {path} failed: {e}")
        return None


def _get(base: str, path: str) -> dict | None:
    try:
        with urllib.request.urlopen(base + path, timeout=55) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        _log(f"get {path} failed: {e}")
        return None


def _budget_ok(task_id: str, budget: int) -> bool:
    counter = Path(os.environ.get("FOREMAN_TMP", ".")) / f"tool_budget_{task_id}"
    try:
        n = int(counter.read_text().strip() or "0")
    except (OSError, ValueError):
        n = 0
    n += 1
    try:
        counter.write_text(str(n))
    except OSError:
        pass
    return n <= budget


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"permissionDecision": "deny", "reason": "bad hook input"}))
        return 0

    base = os.environ.get("FOREMAN_DECISION_URL", "http://127.0.0.1:8000")
    task_id = os.environ.get("FOREMAN_TASK_ID", "0")
    budget = int(os.environ.get("FOREMAN_BUDGET", "80"))

    tool_name = event.get("tool_name") or event.get("toolName") or ""
    tool_input = event.get("tool_input") or event.get("toolInput") or {}

    if not _budget_ok(task_id, budget):
        print(json.dumps({"permissionDecision": "deny", "reason": "tool budget exceeded"}))
        return 0

    if tool_name == "AskUserQuestion":
        question = json.dumps(tool_input, ensure_ascii=False)[:1500]
        created = _post(
            base,
            "/api/internal/decisions",
            {
                "task_id": int(task_id),
                "kind": "ask_user",
                "question": question,
                "tool_name": tool_name,
                "payload": tool_input,
            },
        )
        if not created:
            print(json.dumps({"permissionDecision": "deny", "reason": "decision hub down"}))
            return 0
        did = created.get("id")
        answer = ""
        for _ in range(12):
            result = _get(base, f"/api/internal/decisions/{did}/wait")
            if result and result.get("status") in ("answered", "skipped"):
                answer = result.get("answer") or ""
                break
        updated = dict(tool_input)
        updated["answer"] = answer
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "updatedInput": updated,
                    }
                }
            )
        )
        return 0

    risky = {"Bash", "Write", "Edit", "NotebookEdit"}
    if tool_name in risky and os.environ.get("FOREMAN_INTERACTIVE", "1") == "1":
        summary = f"{tool_name}: {json.dumps(tool_input, ensure_ascii=False)[:300]}"
        _post(
            base,
            "/api/internal/decisions",
            {
                "task_id": int(task_id),
                "kind": "tool_defer",
                "question": summary,
                "tool_name": tool_name,
                "payload": tool_input,
            },
        )
        print(
            json.dumps(
                {
                    "permissionDecision": "defer",
                    "reason": "interactive decision required",
                }
            )
        )
        return 0

    print(json.dumps({"permissionDecision": "allow"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
