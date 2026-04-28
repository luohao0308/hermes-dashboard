from agent.config_evaluator import evaluate_agent_config


def test_evaluate_agent_config_flags_disabled_handoff_target():
    result = evaluate_agent_config({
        "main_agent": "dispatcher",
        "agents": {
            "dispatcher": {
                "name": "Dispatcher",
                "enabled": True,
                "handoffs": ["Developer"],
            },
            "developer": {
                "name": "Developer",
                "enabled": False,
                "handoffs": [],
            },
        },
    })

    assert result["score"] < 100
    assert any("不可用" in item["title"] for item in result["findings"])


def test_evaluate_agent_config_scores_healthy_config():
    result = evaluate_agent_config({
        "main_agent": "dispatcher",
        "agents": {
            "dispatcher": {
                "name": "Dispatcher",
                "enabled": True,
                "handoffs": ["Developer"],
            },
            "developer": {
                "name": "Developer",
                "enabled": True,
                "handoffs": ["Dispatcher"],
            },
        },
    })

    assert result["grade"] == "A"
    assert result["findings"] == []
