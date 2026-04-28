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
