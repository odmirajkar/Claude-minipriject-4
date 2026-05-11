"""
Incident Triage Workflow (WF-02) — TASK 4: Complete this file.

Triggered during a live incident. Chains 4 MCP calls to diagnose
the probable cause and recommend an action.

Output: A JSON dict matching the IncidentReport schema below.
"""
from __future__ import annotations
import json
import time
from typing import TypedDict

from mcp import github_tools, db_tools
from workflows.base import BaseWorkflow


class IncidentReport(TypedDict):
    """The exact JSON schema your workflow must return."""
    service:             str
    error_rate_now:      float    # errors/second in last 5 min
    error_rate_30min_avg: float   # errors/second averaged over 30 min
    likely_cause:        str      # Claude's inference (1–2 sentences)
    recent_deploys:      list[str]  # list of "sha: message" strings
    recommended_action:  str      # specific next step
    escalate:            bool     # True if on-call should be paged


# Fallback returned when parsing fails or a critical error occurs
ESCALATE_FALLBACK: IncidentReport = {
    "service":              "unknown",
    "error_rate_now":       -1.0,
    "error_rate_30min_avg": -1.0,
    "likely_cause":         "Triage workflow failed — see stderr for details",
    "recent_deploys":       [],
    "recommended_action":   "Page on-call immediately — automated triage unavailable",
    "escalate":             True,
}


class IncidentTriageWorkflow(BaseWorkflow):
    name = "incident_triage"

    def execute(self, service_name: str = "payments") -> IncidentReport:
        """
        TASK 4: Implement this method.

        Steps:
          1. Call db_tools.get_error_rate(service_name, window_minutes=30)
          2. Call github_tools.search_recent_commits(self.mcp, self.config.GITHUB_REPO, service_name, hours=4)
          3. Call github_tools.get_priority_issues(self.mcp, self.config.GITHUB_REPO, labels=["bug", service_name])
          4. Call db_tools.get_error_rate(service_name, window_minutes=5)  ← current snapshot
          5. Load prompt with self._load_prompt("incident_triage.txt")
          6. Inject all data into the prompt
          7. Call self.mcp.ask(prompt)
          8. Parse the response as JSON into an IncidentReport dict
          9. Return the dict

        Error handling:
          - If any MCP call raises an exception: log to stderr, use empty data, continue
          - If Claude returns invalid JSON: log raw response to stderr, return ESCALATE_FALLBACK
            with service=service_name set

        Args:
            service_name: The microservice being investigated (e.g. 'payments')

        Returns:
            IncidentReport dict.
        """
        import sys

        # Step 1: Get 30-minute error rate
        try:
            error_rate_30min = db_tools.get_error_rate(service_name, window_minutes=30)
        except Exception as e:
            print(f"Error fetching 30-min error rate for {service_name}: {e}", file=sys.stderr)
            error_rate_30min = {}

        # Step 2: Get recent commits
        try:
            recent_commits = github_tools.search_recent_commits(
                self.mcp, self.config.GITHUB_REPO, service_name, hours=4
            )
        except Exception as e:
            print(f"Error fetching recent commits for {service_name}: {e}", file=sys.stderr)
            recent_commits = []

        # Step 3: Get priority issues (bugs)
        try:
            open_bugs = github_tools.get_priority_issues(
                self.mcp, self.config.GITHUB_REPO, labels=["bug", service_name]
            )
        except Exception as e:
            print(f"Error fetching priority issues for {service_name}: {e}", file=sys.stderr)
            open_bugs = []

        # Step 4: Get 5-minute error rate (current)
        try:
            error_rate_now = db_tools.get_error_rate(service_name, window_minutes=5)
        except Exception as e:
            print(f"Error fetching 5-min error rate for {service_name}: {e}", file=sys.stderr)
            error_rate_now = {}

        # Step 5: Load prompt
        prompt_template = self._load_prompt("incident_triage.txt")

        # Step 6: Format data for injection
        error_rate_30min_value = error_rate_30min.get("error_rate", 0.0)
        error_rate_now_value = error_rate_now.get("error_rate", 0.0)

        commits_data = self._format_commits(recent_commits) if recent_commits else "No recent commits"
        bugs_data = self._format_bugs(open_bugs) if open_bugs else "No open bugs"

        # Inject data into prompt
        prompt = prompt_template.replace("{{SERVICE_NAME}}", service_name)
        prompt = prompt.replace("{{ERROR_RATE_30MIN}}", json.dumps(error_rate_30min))
        prompt = prompt.replace("{{ERROR_RATE_NOW}}", json.dumps(error_rate_now))
        prompt = prompt.replace("{{RECENT_COMMITS}}", commits_data)
        prompt = prompt.replace("{{OPEN_BUGS}}", bugs_data)

        # Step 7: Call Claude
        response = self.mcp.ask(prompt)

        # Step 8: Parse as JSON
        try:
            result = json.loads(response)
            # Ensure it matches the IncidentReport schema
            return {
                "service": result.get("service", service_name),
                "error_rate_now": float(result.get("error_rate_now", 0.0)),
                "error_rate_30min_avg": float(result.get("error_rate_30min_avg", 0.0)),
                "likely_cause": str(result.get("likely_cause", "Unknown")),
                "recent_deploys": result.get("recent_deploys", []),
                "recommended_action": str(result.get("recommended_action", "Investigate")),
                "escalate": bool(result.get("escalate", False)),
            }
        except json.JSONDecodeError as e:
            print(f"Claude returned invalid JSON: {response}", file=sys.stderr)
            fallback = ESCALATE_FALLBACK.copy()
            fallback["service"] = service_name
            return fallback

    def _format_commits(self, commits: list[dict]) -> str:
        """Format commits data for prompt injection."""
        if not commits:
            return "No commits"
        lines = []
        for commit in commits:
            lines.append(
                f"- {commit['sha_short']}: {commit['message']} (by {commit['author']}, {commit['files_changed']} files)"
            )
        return "\n".join(lines)

    def _format_bugs(self, bugs: list[dict]) -> str:
        """Format open bugs data for prompt injection."""
        if not bugs:
            return "No bugs"
        lines = []
        for bug in bugs:
            assignee_str = f"assigned to {bug['assignee']}" if bug['assignee'] != 'unassigned' else "unassigned"
            lines.append(f"- #{bug['number']}: {bug['title']} ({assignee_str}, open {bug['days_open']}d)")
        return "\n".join(lines)
