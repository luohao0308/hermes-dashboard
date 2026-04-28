from agent.config_evaluator import compare_agent_config, evaluate_agent_config


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
    assert any("handoff" in item["title"] for item in result["suggestions"])


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
    assert result["suggestions"][0]["title"] == "保持当前配置"


def test_compare_agent_config_reports_score_delta():
    base = {
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
                "handoffs": ["Dispatcher"],
            },
        },
    }

    result = compare_agent_config(base, {"enabled_overrides": {"developer": True}})

    assert result["candidate"]["score"] > result["current"]["score"]
    assert result["delta"] > 0
    assert "更高" in result["recommendation"]
