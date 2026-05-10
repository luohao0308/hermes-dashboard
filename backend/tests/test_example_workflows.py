"""Example workflow fixtures used for internal trial smoke tests."""

from __future__ import annotations

import json
from pathlib import Path


def test_internal_trial_workflow_fixture_shape():
    path = Path(__file__).resolve().parents[2] / "examples" / "workflows" / "internal_trial_workflow.json"
    data = json.loads(path.read_text())

    assert data["name"]
    assert len(data["nodes"]) >= 3
    assert data["edges"]

    node_ids = {node["node_id"] for node in data["nodes"]}
    assert len(node_ids) == len(data["nodes"])
    for edge in data["edges"]:
        assert edge["from_node"] in node_ids
        assert edge["to_node"] in node_ids

    retry_nodes = [node for node in data["nodes"] if node.get("retry_policy")]
    assert retry_nodes
