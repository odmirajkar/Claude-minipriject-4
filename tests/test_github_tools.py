"""
Unit tests for GitHub MCP tools — provided. Run with: pytest tests/test_github_tools.py
Uses unittest.mock to avoid real MCP calls.
"""
from unittest.mock import MagicMock, patch
import pytest

from mcp import github_tools


@pytest.fixture
def mock_mcp():
    mcp = MagicMock()
    return mcp


@pytest.fixture
def mock_audit():
    with patch("mcp.github_tools._audit") as audit:
        yield audit


# ── get_open_prs ─────────────────────────────────────────────────────────────

def test_get_open_prs_returns_list(mock_mcp, mock_audit):
    mock_mcp.call.return_value = {
        "pull_requests": [
            {"number": 42, "title": "Fix payments timeout", "user": {"login": "alice"},
             "created_at": "2026-04-18T10:00:00Z", "draft": False,
             "reviews": [{"state": "APPROVED"}]},
        ]
    }
    result = github_tools.get_open_prs(mock_mcp, "owner/repo")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["number"] == 42


def test_get_open_prs_excludes_drafts(mock_mcp, mock_audit):
    mock_mcp.call.return_value = {
        "pull_requests": [
            {"number": 1, "title": "Draft PR", "user": {"login": "bob"},
             "created_at": "2026-04-18T10:00:00Z", "draft": True, "reviews": []},
            {"number": 2, "title": "Ready PR", "user": {"login": "carol"},
             "created_at": "2026-04-18T10:00:00Z", "draft": False, "reviews": []},
        ]
    }
    result = github_tools.get_open_prs(mock_mcp, "owner/repo")
    assert len(result) == 1
    assert result[0]["number"] == 2


def test_get_open_prs_returns_empty_on_error(mock_mcp, mock_audit):
    mock_mcp.call.side_effect = Exception("MCP server unavailable")
    result = github_tools.get_open_prs(mock_mcp, "owner/repo")
    assert result == []


def test_get_open_prs_has_required_keys(mock_mcp, mock_audit):
    mock_mcp.call.return_value = {
        "pull_requests": [
            {"number": 5, "title": "Test PR", "user": {"login": "dave"},
             "created_at": "2026-04-22T09:00:00Z", "draft": False, "reviews": []}
        ]
    }
    result = github_tools.get_open_prs(mock_mcp, "owner/repo")
    assert len(result) > 0
    pr = result[0]
    for key in ["number", "title", "author", "days_open", "review_count"]:
        assert key in pr, f"Missing key: {key}"


# ── get_priority_issues ───────────────────────────────────────────────────────

def test_get_priority_issues_returns_list(mock_mcp, mock_audit):
    mock_mcp.call.return_value = {
        "issues": [
            {"number": 100, "title": "Payment crash", "labels": [{"name": "P0"}],
             "assignee": {"login": "eve"}, "created_at": "2026-04-20T08:00:00Z"},
        ]
    }
    result = github_tools.get_priority_issues(mock_mcp, "owner/repo")
    assert len(result) == 1
    assert result[0]["priority"] == "P0"


def test_get_priority_issues_sorted_p0_first(mock_mcp, mock_audit):
    mock_mcp.call.return_value = {
        "issues": [
            {"number": 2, "title": "Minor issue", "labels": [{"name": "P1"}],
             "assignee": None, "created_at": "2026-04-21T08:00:00Z"},
            {"number": 1, "title": "Critical crash", "labels": [{"name": "P0"}],
             "assignee": {"login": "frank"}, "created_at": "2026-04-20T08:00:00Z"},
        ]
    }
    result = github_tools.get_priority_issues(mock_mcp, "owner/repo")
    assert result[0]["priority"] == "P0"


def test_get_priority_issues_returns_empty_on_error(mock_mcp, mock_audit):
    mock_mcp.call.side_effect = RuntimeError("Connection refused")
    result = github_tools.get_priority_issues(mock_mcp, "owner/repo")
    assert result == []


# ── search_recent_commits ─────────────────────────────────────────────────────

def test_search_recent_commits_returns_list(mock_mcp, mock_audit):
    mock_mcp.call.return_value = {
        "commits": [
            {"sha": "abc123def", "author": {"login": "grace"},
             "commit": {"message": "Fix retry logic", "author": {"date": "2026-04-24T10:00:00Z"}},
             "files": [{"filename": "services/payments/retry.py"}]},
        ]
    }
    result = github_tools.search_recent_commits(mock_mcp, "owner/repo", "payments")
    assert isinstance(result, list)


def test_search_recent_commits_has_required_keys(mock_mcp, mock_audit):
    mock_mcp.call.return_value = {
        "commits": [
            {"sha": "abc123def456", "author": {"login": "henry"},
             "commit": {"message": "Update config", "author": {"date": "2026-04-24T11:00:00Z"}},
             "files": [{"filename": "services/orders/config.py"}, {"filename": "services/orders/handler.py"}]},
        ]
    }
    result = github_tools.search_recent_commits(mock_mcp, "owner/repo", "orders")
    if result:
        commit = result[0]
        for key in ["sha_short", "author", "message", "timestamp", "files_changed"]:
            assert key in commit, f"Missing key: {key}"


def test_search_recent_commits_returns_empty_on_error(mock_mcp, mock_audit):
    mock_mcp.call.side_effect = Exception("Timeout")
    result = github_tools.search_recent_commits(mock_mcp, "owner/repo", "payments")
    assert result == []
