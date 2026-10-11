"""Test double for Claude Code CLI. Emits stream-json lines.

Prompt containing FAIL -> exit 1. Prompt containing ASK -> emits AskUserQuestion.
Flags:
  --quota-after N          emit rate limit marker after N assistant messages
  --quota-resets-in SECS   include "resets in N seconds" hint (default 60)
"""

import json
import sys
import time
import uuid


def main() -> int:
    args = sys.argv[1:]
    prompt = ""
    session_id = str(uuid.uuid4())
    resume = None
    quota_after = None
    quota_resets_in = 60
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-p" or a == "--print":
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                prompt = args[i + 1]
                i += 1
        elif a == "--session-id" and i + 1 < len(args):
            session_id = args[i + 1]
            i += 1
        elif a == "--resume" and i + 1 < len(args):
            resume = args[i + 1]
            i += 1
        elif a == "--quota-after" and i + 1 < len(args):
            quota_after = int(args[i + 1])
            i += 1
        elif a == "--quota-resets-in" and i + 1 < len(args):
            quota_resets_in = int(args[i + 1])
            i += 1
        i += 1

    if resume:
        session_id = resume

    def emit(obj: dict) -> None:
        sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    emit(
        {
            "type": "system",
            "subtype": "init",
            "session_id": session_id,
            "model": "fake-claude",
            "cwd": ".",
            "tools": ["Bash", "Read", "Write"],
        }
    )
    time.sleep(0.02)

    if "ASK" in prompt:
        emit(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "t1",
                            "name": "AskUserQuestion",
                            "input": {"question": "选哪个模块？", "options": [{"label": "A"}, {"label": "B"}]},
                        }
                    ],
                },
            }
        )
        emit(
            {
                "type": "result",
                "subtype": "error_during_execution",
                "is_error": True,
                "result": "waiting for user decision",
                "session_id": session_id,
                "num_turns": 1,
                "total_cost_usd": 0.01,
            }
        )
        return 0

    if quota_after is not None:
        for n in range(quota_after):
            emit(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": f"step {n + 1}: working"}],
                    },
                }
            )
            time.sleep(0.01)
        emit(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"usage limit reached. try again in {quota_resets_in} seconds. "
                                "your limit will reset at the next window."
                            ),
                        }
                    ],
                },
            }
        )
        return 0

    emit(
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": f"working on: {prompt[:80]}"},
                    {
                        "type": "tool_use",
                        "id": "t1",
                        "name": "Bash",
                        "input": {"command": "echo hello"},
                    },
                ],
            },
        }
    )
    time.sleep(0.02)
    emit(
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "hello\n"}],
            },
        }
    )

    if "FAIL" in prompt:
        emit(
            {
                "type": "result",
                "subtype": "error_during_execution",
                "is_error": True,
                "result": "simulated failure",
                "session_id": session_id,
                "num_turns": 2,
                "total_cost_usd": 0.02,
            }
        )
        return 1

    emit(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": f"done: {prompt[:80]}",
            "session_id": session_id,
            "num_turns": 2,
            "total_cost_usd": 0.05,
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

