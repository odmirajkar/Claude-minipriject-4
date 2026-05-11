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
        raise NotImplementedError("Task 4: implement IncidentTriageWorkflow.execute()")
