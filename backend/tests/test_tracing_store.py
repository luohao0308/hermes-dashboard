from agent.tracing_store import TraceStore


def test_trace_store_persists_runs_and_spans(tmp_path):
    db_path = tmp_path / "traces.sqlite3"
    store = TraceStore(db_path=str(db_path))

    run_id = store.create_run(
        session_id="chat-1",
        agent_id="Developer",
        linked_session_id="hermes-1",
        input_summary="debug this",
    )
    store.add_span(
        run_id,
        span_type="user_input",
        title="User message",
        summary="debug this",
        agent_name="Developer",
    )
    store.complete_run(run_id)

    restored = TraceStore(db_path=str(db_path))
    run = restored.get_run(run_id)
    spans = restored.list_spans(run_id)
    latest = restored.find_latest_run(linked_session_id="hermes-1")

    assert run is not None
    assert run["status"] == "completed"
    assert latest is not None
    assert latest["run_id"] == run_id
    assert len(spans) == 1
    assert spans[0]["span_type"] == "user_input"


def test_trace_store_persists_rca_reports(tmp_path):
    db_path = tmp_path / "traces.sqlite3"
    store = TraceStore(db_path=str(db_path))

    saved = store.save_rca_report(
        session_id="hermes-1",
        run_id="run-1",
        report={
            "category": "tool",
            "root_cause": "工具或 handoff 失败",
            "confidence": 0.82,
            "evidence": [{"source": "trace", "detail": "tool failed"}],
            "next_actions": ["重放工具调用"],
        },
    )

    restored = TraceStore(db_path=str(db_path))
    latest = restored.get_latest_rca_report("hermes-1")

    assert saved["report_id"]
    assert latest is not None
    assert latest["report_id"] == saved["report_id"]
    assert latest["category"] == "tool"
