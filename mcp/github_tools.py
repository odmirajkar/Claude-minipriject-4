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
    start = time.time()
    tool_input = {"repo": repo, "state": "open"}

    try:
        result = mcp.call("github_pull_requests", tool_input)
        duration_ms = int((time.time() - start) * 1000)
        _audit.log(workflow="github_tools", tool="github_pull_requests", tool_input=tool_input, status="success", duration_ms=duration_ms)

        if not result:
            return []

        # Extract pull_requests list from response
        prs = result.get("pull_requests", []) if isinstance(result, dict) else result
        if not isinstance(prs, list):
            return []

        now = datetime.now(timezone.utc)
        output = []

        for pr in prs:
            # Skip draft PRs
            if pr.get("draft", False):
                continue

            # Parse created_at timestamp
            try:
                created_at = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue

            days_open = (now - created_at).days

            # Filter by minimum age
            if days_open < min_age_days:
                continue

            output.append({
                "number": pr["number"],
                "title": pr["title"],
                "author": pr["user"]["login"] if pr.get("user") else "unknown",
                "days_open": days_open,
                "review_count": pr.get("review_comments", 0),
            })

        return output

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        _audit.log(workflow="github_tools", tool="github_pull_requests", tool_input=tool_input, status="error", duration_ms=duration_ms)
        print(f"Error fetching open PRs for {repo}: {e}", file=__import__("sys").stderr)
        return []


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

    start = time.time()
    tool_input = {"repo": repo, "state": "open", "labels": labels}

    try:
        result = mcp.call("github_issues", tool_input)
        duration_ms = int((time.time() - start) * 1000)
        _audit.log(workflow="github_tools", tool="github_issues", tool_input=tool_input, status="success", duration_ms=duration_ms)

        if not result:
            return []

        # Extract issues list from response
        issues = result.get("issues", []) if isinstance(result, dict) else result
        if not isinstance(issues, list):
            return []

        now = datetime.now(timezone.utc)
        output = []

        for issue in issues:
            # Extract priority from issue labels
            issue_labels = [label.get("name", "") if isinstance(label, dict) else label for label in issue.get("labels", [])]
            priority = None
            for label in labels:
                if label in issue_labels:
                    priority = label
                    break

            if priority is None:
                continue

            # Parse created_at timestamp
            try:
                created_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue

            days_open = (now - created_at).days

            assignee = "unassigned"
            if issue.get("assignee"):
                assignee = issue["assignee"].get("login", "unassigned")

            output.append({
                "number": issue["number"],
                "title": issue["title"],
                "priority": priority,
                "assignee": assignee,
                "days_open": days_open,
            })

        # Sort by priority (P0 first), then by days_open descending
        priority_order = {label: i for i, label in enumerate(labels)}
        output.sort(key=lambda x: (priority_order.get(x["priority"], 999), -x["days_open"]))

        return output

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        _audit.log(workflow="github_tools", tool="github_issues", tool_input=tool_input, status="error", duration_ms=duration_ms)
        print(f"Error fetching priority issues for {repo}: {e}", file=__import__("sys").stderr)
        return []


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
    start = time.time()
    tool_input = {"repo": repo, "path": f"services/{service}/"}

    try:
        result = mcp.call("github_commits", tool_input)
        duration_ms = int((time.time() - start) * 1000)
        _audit.log(workflow="github_tools", tool="github_commits", tool_input=tool_input, status="success", duration_ms=duration_ms)

        if not result:
            return []

        # Extract commits list from response
        commits = result.get("commits", []) if isinstance(result, dict) else result
        if not isinstance(commits, list):
            return []

        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=hours)
        output = []

        for commit in commits:
            # Parse timestamp from commit.author.date
            try:
                commit_data = commit.get("commit", {})
                timestamp_str = commit_data.get("author", {}).get("date", "")
                commit_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue

            # Filter by time window
            if commit_time < cutoff_time:
                continue

            # Extract first line of commit message
            message = commit.get("commit", {}).get("message", "").split("\n")[0]

            # Get author - try login first, fallback to commit author name
            author = "unknown"
            if commit.get("author") and isinstance(commit["author"], dict):
                author = commit["author"].get("login", "unknown")

            output.append({
                "sha_short": commit["sha"][:7] if commit.get("sha") else "unknown",
                "author": author,
                "message": message,
                "timestamp": timestamp_str,
                "files_changed": len(commit.get("files", [])) if commit.get("files") else 0,
            })

        return output

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        _audit.log(workflow="github_tools", tool="github_commits", tool_input=tool_input, status="error", duration_ms=duration_ms)
        print(f"Error fetching recent commits for {repo} service {service}: {e}", file=__import__("sys").stderr)
        return []
