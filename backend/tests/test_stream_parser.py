import json

from app.services.stream_parser import StreamParser, detect_rate_limit


def test_parse_init_and_result():
    p = StreamParser()
    events = p.feed(
        json.dumps({"type": "system", "subtype": "init", "session_id": "s1", "model": "opus"})
    )
    assert p.session_id == "s1"
    assert events[0].log_type == "system"

    events = p.feed(
        json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "result": "all done",
                "num_turns": 3,
                "total_cost_usd": 0.1,
                "session_id": "s1",
            }
        )
    )
    assert p.num_turns == 3
    assert p.result_text == "all done"
    assert not p.is_error
    assert events[0].log_type == "result"


def test_parse_tool_use_and_ask():
    p = StreamParser()
    line = json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "hello"},
                    {
                        "type": "tool_use",
                        "id": "t1",
                        "name": "AskUserQuestion",
                        "input": {"question": "选哪个？"},
                    },
                ]
            },
        }
    )
    events = p.feed(line)
    types = [e.type for e in events]
    assert "decision" in types
    assert p.tool_call_count == 1


def test_plain_fallback():
    p = StreamParser()
    events = p.feed("not json at all")
    assert p.plain_mode
    assert events[0].log_type == "stdout"


def test_decision_marker():
    p = StreamParser()
    events = p.feed(json.dumps({"type": "result", "result": "请确认【需人工决策】下一步"}))
    decs = [e for e in events if e.type == "decision"]
    assert len(decs) == 1
    assert decs[0].extra["kind"] == "text_marker"


def test_detect_rate_limit():
    assert detect_rate_limit("Error: usage limit reached") is not None
    assert detect_rate_limit("hello world") is None
    info = detect_rate_limit("Your limit will reset at 5pm")
    assert info is not None
