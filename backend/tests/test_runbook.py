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
    assert runbook["execution_steps"][0]["label"] == "重放工具调用"


def test_generate_runbook_marks_repair_steps_for_confirmation():
    runbook = generate_runbook(
        {"task_id": "session-2", "status": "failed", "name": "Deploy"},
        rca={
            "report_id": "rca-2",
            "root_cause": "部署失败",
            "confidence": 0.9,
            "evidence": [{"severity": "high"}],
            "next_actions": ["重启 Gateway 服务", "确认最新 trace 正常"],
        },
        run=None,
        spans=[],
    )

    restart_step = runbook["execution_steps"][0]
    assert restart_step["requires_confirmation"] is True
    assert restart_step["status"] == "needs_confirmation"
