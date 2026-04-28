from agent.exporter import build_session_export, list_markdown_exports, save_markdown_export


def test_build_session_export_includes_rca_and_runbook():
    content = build_session_export(
        "session-123",
        rca={
            "root_cause": "工具失败",
            "confidence": 0.8,
            "evidence": [{"source": "trace", "title": "Tool", "detail": "failed"}],
        },
        runbook={"markdown": "# Runbook\n\n- [ ] retry"},
    )

    assert "工具失败" in content
    assert "Confidence: 80%" in content
    assert "# Runbook" in content


def test_save_markdown_export_writes_file(tmp_path):
    saved = save_markdown_export(str(tmp_path), "session/123", "# Hello\n")

    assert saved["filename"].endswith(".md")
    assert saved["bytes"] > 0
    assert (tmp_path / saved["filename"]).read_text(encoding="utf-8") == "# Hello\n"


def test_list_markdown_exports_returns_recent_files(tmp_path):
    save_markdown_export(str(tmp_path), "session-1", "# One\n")

    result = list_markdown_exports(str(tmp_path))

    assert result["exists"] is True
    assert result["count"] == 1
    assert result["files"][0]["filename"].endswith(".md")
