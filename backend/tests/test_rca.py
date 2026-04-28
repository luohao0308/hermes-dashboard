from agent.rca import analyze_failure


def test_rca_classifies_tool_trace_failure():
    report = analyze_failure(
        {
            "task_id": "session-1",
            "status": "failed",
            "message_count": 2,
            "end_reason": "error",
        },
        logs=[],
        run={"run_id": "run-1", "status": "error"},
        spans=[
            {
                "span_id": "span-1",
                "span_type": "tool",
                "title": "Tool failed",
                "summary": "get_logs tool call failed with validation error",
                "status": "error",
                "started_at": "2026-04-28T08:00:00",
            }
        ],
    )

    assert report["category"] == "tool"
    assert report["confidence"] >= 0.8
    assert report["root_cause"] == "工具或 handoff 失败"
    assert report["evidence"][0]["source"] == "session"
    assert any(item["source"] == "trace" for item in report["evidence"])


def test_rca_marks_missing_session_data_low_confidence():
    report = analyze_failure(
        {"task_id": "session-2", "status": "completed", "messages": [], "message_count": 0},
        logs=[],
        run=None,
        spans=[],
    )

    assert report["category"] == "data"
    assert report["low_confidence"] is True
    assert "原始 trace" in report["next_actions"][-1]
