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


def test_nested_workflow_fixture_shape():
    path = Path(__file__).resolve().parents[2] / "examples" / "workflows" / "nested_workflow_example.json"
    data = json.loads(path.read_text())

    assert data["name"] == "Nested Workflow Example"
    assert "child workflow" in data["description"].lower()
    assert data["is_reusable"] is False
    assert len(data["nodes"]) >= 4
    assert len(data["edges"]) >= 3

    # Verify subworkflow node exists
    subworkflow_nodes = [n for n in data["nodes"] if n.get("task_type") == "subworkflow"]
    assert len(subworkflow_nodes) == 1
    sub_node = subworkflow_nodes[0]
    assert "child_workflow_id" in sub_node
    assert sub_node["child_workflow_id"] == "PLACEHOLDER_REPLACE_WITH_CHILD_WORKFLOW_ID"

    # Verify approval node exists
    approval_nodes = [n for n in data["nodes"] if n.get("task_type") == "approval"]
    assert len(approval_nodes) >= 1

    # Verify edge connectivity
    node_ids = {node["node_id"] for node in data["nodes"]}
    for edge in data["edges"]:
        assert edge["from_node"] in node_ids
        assert edge["to_node"] in node_ids

    # Verify metadata structure
    assert "metadata_json" in data
    assert "setup_instructions" in data["metadata_json"]
    assert "nested_workflow_features" in data["metadata_json"]
