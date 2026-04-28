from agent.config_history import ConfigHistory


def test_config_history_records_summaries(tmp_path):
    history = ConfigHistory(path=str(tmp_path / "history.jsonl"))
    before = {
        "main_agent": "dispatcher",
        "agents": {
            "dispatcher": {"name": "Dispatcher", "enabled": True, "handoffs": ["Developer"]},
            "developer": {"name": "Developer", "enabled": True, "handoffs": ["Dispatcher"]},
        },
        "custom_agents": [],
    }
    after = {
        **before,
        "main_agent": "developer",
    }

    event = history.record("set_main_agent", before, after, target="developer")
    events = history.list_events()

    assert event["action"] == "set_main_agent"
    assert events[0]["event_id"] == event["event_id"]
    assert events[0]["before"]["main_agent"] == "dispatcher"
    assert events[0]["after"]["main_agent"] == "developer"
    assert events[0]["after"]["enabled_count"] == 2
