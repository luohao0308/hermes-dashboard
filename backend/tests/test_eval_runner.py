from agent.eval_runner import run_eval_samples
from agent.tools.hermes_tools import list_tool_specs


def test_run_eval_samples_scores_local_contract():
    result = run_eval_samples(
        agent_config={
            "agents": {
                "developer": {"name": "Developer", "enabled": True},
                "reviewer": {"name": "Reviewer", "enabled": True},
                "researcher": {"name": "Researcher", "enabled": True},
                "monitor": {"name": "Monitor", "enabled": True},
                "executor": {"name": "Executor", "enabled": True},
            }
        },
        tool_specs=list_tool_specs(),
    )

    assert result["mode"] == "offline_contract"
    assert result["count"] == 5
    assert result["passed"] == 5
    assert result["avg_score"] == 100


def test_run_eval_samples_flags_missing_agent_and_tools():
    result = run_eval_samples(
        category="monitor",
        agent_config={"agents": {"developer": {"name": "Developer", "enabled": True}}},
        tool_specs=[],
    )

    assert result["count"] == 1
    assert result["failed"] == 1
    assert result["results"][0]["passed"] is False
    codes = {finding["code"] for finding in result["results"][0]["findings"]}
    assert "expected_agent_missing" in codes
    assert "missing_tools" in codes
