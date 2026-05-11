"""
Morning Intelligence Brief Workflow (WF-01) — TASK 3: Complete this file.

This workflow runs every morning and gives the FinTrack engineering team
a concise, data-driven overview of what needs attention.

Data sources:
  - GitHub: open PRs needing review, open P0/P1 issues
  - PostgreSQL: services with elevated error rates overnight

Output: A markdown string with 4 required sections (see task description).
"""
from __future__ import annotations
import time

from mcp import github_tools, db_tools
from workflows.base import BaseWorkflow


class MorningBriefWorkflow(BaseWorkflow):
    name = "morning_brief"

    def execute(self) -> str:
        """
        TASK 3: Implement this method.

        Steps:
          1. Call github_tools.get_open_prs(self.mcp, self.config.GITHUB_REPO)
          2. Call github_tools.get_priority_issues(self.mcp, self.config.GITHUB_REPO)
          3. Call db_tools.get_overnight_alerts()
          4. Load the prompt template with self._load_prompt("morning_brief.txt")
          5. Inject the data into the prompt (replace placeholders or format inline)
          6. Call self.mcp.ask(prompt) to get Claude's formatted response
          7. Return the response string

        The returned string must contain these exact section headers:
            ## PRs_NEEDING_REVIEW
            ## OPEN_P0_P1
            ## OVERNIGHT_DB_ALERTS
            ## ACTION_ITEMS

        If a data source returns an empty list, include the section header with:
            "No data returned from [source_name]"

        Returns:
            str: The formatted markdown brief.
        """
        # Step 1: Fetch open PRs
        prs = github_tools.get_open_prs(self.mcp, self.config.GITHUB_REPO)

        # Step 2: Fetch priority issues
        issues = github_tools.get_priority_issues(self.mcp, self.config.GITHUB_REPO)

        # Step 3: Fetch overnight alerts
        alerts = db_tools.get_overnight_alerts()

        # Step 4: Load prompt template
        prompt_template = self._load_prompt("morning_brief.txt")

        # Step 5: Format data for injection into prompt
        pr_data = self._format_prs(prs) if prs else "No data returned from github_pull_requests"
        issue_data = self._format_issues(issues) if issues else "No data returned from github_issues"
        alert_data = self._format_alerts(alerts) if alerts else "No data returned from db_overnight_alerts"

        # Inject data into prompt
        prompt = prompt_template.replace("{{PR_DATA}}", pr_data)
        prompt = prompt.replace("{{ISSUE_DATA}}", issue_data)
        prompt = prompt.replace("{{ALERT_DATA}}", alert_data)

        # Step 6: Call Claude to synthesize the brief
        response = self.mcp.ask(prompt)

        # Step 7: Return response
        return response

    def _format_prs(self, prs: list[dict]) -> str:
        """Format PR data for prompt injection."""
        if not prs:
            return "No PRs"
        lines = []
        for pr in prs:
            lines.append(f"- PR #{pr['number']}: {pr['title']} (by {pr['author']}, open {pr['days_open']}d, {pr['review_count']} reviews)")
        return "\n".join(lines)

    def _format_issues(self, issues: list[dict]) -> str:
        """Format issue data for prompt injection."""
        if not issues:
            return "No issues"
        lines = []
        for issue in issues:
            assignee_str = f"assigned to {issue['assignee']}" if issue['assignee'] != 'unassigned' else "unassigned"
            lines.append(f"- [{issue['priority']}] #{issue['number']}: {issue['title']} ({assignee_str}, open {issue['days_open']}d)")
        return "\n".join(lines)

    def _format_alerts(self, alerts: list[dict]) -> str:
        """Format overnight alert data for prompt injection."""
        if not alerts:
            return "No alerts"
        lines = []
        for alert in alerts:
            lines.append(f"- {alert['service']}: error rate {alert['error_rate']}/s (baseline {alert['baseline']}/s, +{alert['delta_pct']}%) at {alert['hour_utc']}:00 UTC")
        return "\n".join(lines)
