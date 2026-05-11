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
        raise NotImplementedError("Task 3: implement MorningBriefWorkflow.execute()")
