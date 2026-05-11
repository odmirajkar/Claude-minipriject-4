"""
GitHub MCP Tool Wrappers — TASK 2: Complete this file.

Each function wraps one or more GitHub MCP tool calls, handles errors
gracefully (returning [] on failure), and logs every call via AuditLogger.

The caller (workflow code) should never see an exception from this module.
"""
from __future__ import annotations
import time
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

from mcp.audit import AuditLogger

if TYPE_CHECKING:
    from mcp.client import MCPClient


_audit = AuditLogger()


def get_open_prs(mcp: "MCPClient", repo: str, min_age_days: int = 1) -> list[dict]:
    """
    Fetch open, non-draft pull requests older than min_age_days.

    TASK 2: Implement this function.

    Args:
        mcp:          The MCPClient context (use mcp.call())
        repo:         GitHub repo in 'owner/repo' format
        min_age_days: Only return PRs open for at least this many days

    Returns:
        List of dicts, each with:
            number       (int)   PR number
            title        (str)   PR title
            author       (str)   GitHub username of author
            days_open    (int)   How many days the PR has been open
            review_count (int)   Number of reviews already submitted

        Returns [] on any error (log the error first).

    Hint:
        - Call mcp.call("github_pull_requests", {"repo": repo, "state": "open"})
        - Filter out draft PRs from the result
        - Calculate days_open from the 'created_at' timestamp in the response
        - Log the call with _audit.log() after it completes
    """
    raise NotImplementedError("Task 2: implement get_open_prs()")


def get_priority_issues(
    mcp: "MCPClient",
    repo: str,
    labels: list[str] | None = None,
) -> list[dict]:
    """
    Fetch open issues matching any of the given labels.

    TASK 2: Implement this function.

    Args:
        mcp:    The MCPClient context
        repo:   GitHub repo in 'owner/repo' format
        labels: List of label names to filter by (default: ['P0', 'P1'])

    Returns:
        List of dicts, each with:
            number   (int)  Issue number
            title    (str)  Issue title
            priority (str)  'P0' or 'P1' (extracted from labels)
            assignee (str)  GitHub username, or 'unassigned'
            days_open (int) How many days the issue has been open

        Sorted by priority (P0 first), then by days_open descending.
        Returns [] on any error.
    """
    if labels is None:
        labels = ["P0", "P1"]
    raise NotImplementedError("Task 2: implement get_priority_issues()")


def search_recent_commits(
    mcp: "MCPClient",
    repo: str,
    service: str,
    hours: int = 4,
) -> list[dict]:
    """
    Find commits touching files under services/{service}/ in the last N hours.

    TASK 2: Implement this function.

    Args:
        mcp:     The MCPClient context
        repo:    GitHub repo in 'owner/repo' format
        service: Service name (e.g. 'payments' → looks in services/payments/)
        hours:   How many hours back to search

    Returns:
        List of dicts, each with:
            sha_short     (str)  First 7 chars of commit SHA
            author        (str)  GitHub username
            message       (str)  First line of commit message
            timestamp     (str)  ISO 8601 UTC timestamp
            files_changed (int)  Number of files changed in the commit

        Returns [] on any error.

    Hint:
        - Use mcp.call("github_commits", {"repo": repo, "path": f"services/{service}/"})
        - Filter by timestamp to only return commits within the last N hours
    """
    raise NotImplementedError("Task 2: implement search_recent_commits()")
