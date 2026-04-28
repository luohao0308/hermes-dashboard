from agent.eval_samples import get_eval_sample_summary, list_eval_samples


def test_eval_samples_cover_required_categories():
    samples = list_eval_samples()
    categories = {sample["category"] for sample in samples}

    assert {"debug", "review", "research", "deploy", "monitor"}.issubset(categories)
    assert all(sample["sample_id"] for sample in samples)
    assert all(sample["success_criteria"] for sample in samples)


def test_eval_samples_filter_by_category():
    samples = list_eval_samples(category="debug")

    assert len(samples) == 1
    assert samples[0]["category"] == "debug"
    assert "get_logs" in samples[0]["expected_tools"]


def test_eval_sample_summary_counts_categories_and_risks():
    summary = get_eval_sample_summary()

    assert summary["total"] == 5
    assert summary["categories"]["deploy"] == 1
    assert "confirm" in summary["risk_levels"]
