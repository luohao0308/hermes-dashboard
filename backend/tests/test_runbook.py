from agent.runbook import generate_runbook


def test_generate_runbook_uses_rca_evidence_and_actions():
    runbook = generate_runbook(
        {
            "task_id": "session-1",
            "name": "失败任务",
            "status": "failed",
        },
        rca={
            "report_id": "rca-1",
            "root_cause": "工具或 handoff 失败",
            "confidence": 0.82,
            "evidence": [
                {
                    "source": "trace",
                    "title": "Tool failed",
                    "detail": "get_logs validation error",
                    "severity": "high",
                }
            ],
            "next_actions": ["重放工具调用"],
        },
        run={"run_id": "run-1"},
        spans=[{"span_id": "span-1"}],
    )

    assert runbook["severity"] == "high"
    assert runbook["rca_report_id"] == "rca-1"
    assert "工具或 handoff 失败" in runbook["markdown"]
    assert "重放工具调用" in runbook["checklist"]
