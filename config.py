"""
Configuration loader — reads from .env file.
All sensitive values come from environment variables only.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GITHUB_TOKEN:   str = os.getenv("FINTRACK_GITHUB_TOKEN", "")
    PG_READ_URL:    str = os.getenv("FINTRACK_PG_READ_URL", "")
    JIRA_TOKEN:     str = os.getenv("FINTRACK_JIRA_TOKEN", "")
    JIRA_BASE_URL:  str = os.getenv("FINTRACK_JIRA_BASE_URL", "")
    SLACK_WEBHOOK:  str = os.getenv("FINTRACK_SLACK_WEBHOOK", "")
    GITHUB_REPO:    str = os.getenv("FINTRACK_GITHUB_REPO", "instructor/fintrack-backend-lab")
    CLAUDE_MODEL:   str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    def check(self) -> dict[str, bool]:
        """Return connection status for each MCP server."""
        return {
            "github-mcp": bool(self.GITHUB_TOKEN),
            "pg-mcp":     bool(self.PG_READ_URL),
            "jira-mcp":   bool(self.JIRA_TOKEN),
            "slack":      bool(self.SLACK_WEBHOOK),
        }


config = Config()
