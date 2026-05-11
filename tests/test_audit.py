"""
Unit tests for AuditLogger — provided. Run with: pytest tests/test_audit.py
"""
import json
import tempfile
from pathlib import Path

import pytest

from mcp.audit import AuditLogger


@pytest.fixture
def tmp_logger(tmp_path):
    return AuditLogger(log_path=tmp_path / "audit.log")


def test_log_creates_file(tmp_logger):
    tmp_logger.log(
        workflow="test_wf", tool="github_issues",
        tool_input={"repo": "owner/repo"}, status="success", duration_ms=100,
    )
    assert tmp_logger.log_path.exists()


def test_log_entry_has_required_fields(tmp_logger):
    tmp_logger.log(
        workflow="morning_brief", tool="github_pull_requests",
        tool_input={"repo": "owner/repo", "state": "open"},
        status="success", duration_ms=342,
    )
    lines = tmp_logger.log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    for field in ["timestamp", "workflow", "tool", "input_hash", "status", "duration_ms"]:
        assert field in entry, f"Missing field: {field}"


def test_log_does_not_store_raw_input(tmp_logger):
    sensitive_input = {"repo": "owner/repo", "token": "ghp_secret123"}
    tmp_logger.log(
        workflow="test", tool="github_issues",
        tool_input=sensitive_input, status="success", duration_ms=50,
    )
    raw = tmp_logger.log_path.read_text()
    assert "ghp_secret123" not in raw
    assert "token" not in raw


def test_input_hash_is_sha256(tmp_logger):
    tmp_logger.log(
        workflow="test", tool="github_issues",
        tool_input={"repo": "owner/repo"}, status="success", duration_ms=10,
    )
    entry = json.loads(tmp_logger.log_path.read_text().strip())
    # SHA-256 hex digest is always 64 characters
    assert len(entry["input_hash"]) == 64


def test_multiple_entries_appended(tmp_logger):
    for i in range(5):
        tmp_logger.log(
            workflow="wf", tool=f"tool_{i}",
            tool_input={}, status="success", duration_ms=i * 10,
        )
    lines = tmp_logger.log_path.read_text().strip().splitlines()
    assert len(lines) == 5


def test_error_status_logged(tmp_logger):
    tmp_logger.log(
        workflow="test", tool="github_issues",
        tool_input={}, status="error", duration_ms=5,
    )
    entry = json.loads(tmp_logger.log_path.read_text().strip())
    assert entry["status"] == "error"


def test_recent_returns_last_n(tmp_logger):
    for i in range(10):
        tmp_logger.log(workflow="wf", tool=f"tool_{i}", tool_input={}, status="success", duration_ms=i)
    recent = tmp_logger.recent(n=3)
    assert len(recent) == 3
    assert recent[-1]["tool"] == "tool_9"
