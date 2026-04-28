import pytest

from agent.structured_guardrails import validate_agent_input, validate_rca_output


def test_validate_agent_input_allows_normal_message():
    result = validate_agent_input({
        "session_id": "chat-1",
        "agent_id": "main",
        "linked_session_id": "session-1",
        "message": "帮我分析失败原因",
    })

    assert result["decision"] == "allow"
    assert result["payload"]["message"] == "帮我分析失败原因"


def test_validate_agent_input_blocks_invalid_message():
    result = validate_agent_input({
        "session_id": "chat-1",
        "agent_id": "main",
        "message": "\x00",
    })

    assert result["decision"] == "deny"


def test_validate_rca_output_requires_structured_evidence():
    report = {
        "report_id": "",
        "session_id": "session-1",
        "run_id": None,
        "category": "tool",
        "root_cause": "工具失败",
        "confidence": 0.8,
        "evidence": [
            {
                "source": "trace",
                "title": "Tool failed",
                "detail": "get_logs failed",
                "severity": "high",
            }
        ],
        "next_actions": ["重放工具调用"],
        "low_confidence": False,
        "generated_at": "2026-04-29T00:00:00",
        "analyzer": "test",
    }

    normalized = validate_rca_output(report)

    assert normalized["category"] == "tool"
    assert normalized["evidence"][0]["source"] == "trace"


def test_validate_rca_output_rejects_bad_confidence():
    report = {
        "report_id": "",
        "session_id": "session-1",
        "category": "tool",
        "root_cause": "工具失败",
        "confidence": 2,
        "evidence": [],
        "next_actions": ["重放工具调用"],
        "low_confidence": False,
        "generated_at": "2026-04-29T00:00:00",
        "analyzer": "test",
    }

    with pytest.raises(Exception):
        validate_rca_output(report)
