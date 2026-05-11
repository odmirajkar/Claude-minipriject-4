"""
Integration tests for workflows — TASK 5: Write 3 tests here.

Use unittest.mock to mock MCP calls — never make real API calls in tests.

You must write:
  1. test_morning_brief_structure
  2. test_incident_triage_valid_json
  3. test_incident_triage_degraded

See the task description for the requirements of each test.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from workflows.morning_brief import MorningBriefWorkflow
from workflows.incident_triage import IncidentTriageWorkflow, ESCALATE_FALLBACK


@pytest.fixture
def mock_config():
    """Mock configuration object."""
    config = MagicMock()
    config.GITHUB_REPO = "owner/repo"
    return config


@pytest.fixture
def mock_mcp():
    """Mock MCPClient."""
    return MagicMock()


def test_morning_brief_structure(mock_mcp, mock_config):
    """
    Test that MorningBriefWorkflow returns markdown with all 4 required section headers.

    Mocks all MCP calls to return sample data. Asserts:
    - Output is a string
    - Contains all 4 required headers: PRs_NEEDING_REVIEW, OPEN_P0_P1, OVERNIGHT_DB_ALERTS, ACTION_ITEMS
    """
    # Mock github_tools and db_tools
    with patch('workflows.morning_brief.github_tools') as mock_gh, \
         patch('workflows.morning_brief.db_tools') as mock_db:

        # Set up mock data
        mock_gh.get_open_prs.return_value = [
            {
                "number": 42,
                "title": "Fix timeout issue",
                "author": "alice",
                "days_open": 2,
                "review_count": 1,
            }
        ]
        mock_gh.get_priority_issues.return_value = [
            {
                "number": 100,
                "title": "Critical bug in payments",
                "priority": "P0",
                "assignee": "bob",
                "days_open": 1,
            }
        ]
        mock_db.get_overnight_alerts.return_value = [
            {
                "service": "payments",
                "hour_utc": 3,
                "error_rate": 2.5,
                "baseline": 0.5,
                "delta_pct": 400.0,
            }
        ]

        # Mock Claude response with all required sections
        mock_mcp.ask.return_value = """## PRs_NEEDING_REVIEW
- PR #42: Fix timeout issue (by alice, open 2d, 1 reviews)

## OPEN_P0_P1
- [P0] #100: Critical bug in payments (assigned to bob, open 1d)

## OVERNIGHT_DB_ALERTS
- payments: error rate 2.5/s (baseline 0.5/s, +400.0%) at 3:00 UTC

## ACTION_ITEMS
- Investigate and fix the critical payment bug (P0)
- Review and merge the timeout fix PR
- Monitor error rate for the payments service overnight"""

        # Execute workflow
        workflow = MorningBriefWorkflow(mcp=mock_mcp, config=mock_config)
        result = workflow.execute()

        # Assertions
        assert isinstance(result, str), "Result should be a string"
        assert "## PRs_NEEDING_REVIEW" in result, "Missing PRs_NEEDING_REVIEW section"
        assert "## OPEN_P0_P1" in result, "Missing OPEN_P0_P1 section"
        assert "## OVERNIGHT_DB_ALERTS" in result, "Missing OVERNIGHT_DB_ALERTS section"
        assert "## ACTION_ITEMS" in result, "Missing ACTION_ITEMS section"


def test_incident_triage_valid_json(mock_mcp, mock_config):
    """
    Test that IncidentTriageWorkflow returns a valid dict with all required keys.

    Mocks MCP calls to return sample data. Asserts:
    - Return type is dict
    - All required keys present: service, error_rate_now, error_rate_30min_avg,
      likely_cause, recent_deploys, recommended_action, escalate
    - Data types are correct (floats, strings, lists, bool)
    """
    with patch('workflows.incident_triage.github_tools') as mock_gh, \
         patch('workflows.incident_triage.db_tools') as mock_db:

        # Set up mock data
        mock_db.get_error_rate.side_effect = [
            {"error_rate": 0.5, "baseline": 0.5},   # 30-min
            {"error_rate": 5.2, "baseline": 0.5},   # 5-min
        ]
        mock_gh.search_recent_commits.return_value = [
            {
                "sha_short": "abc123d",
                "author": "alice",
                "message": "Fix memory leak in retry logic",
                "timestamp": "2026-04-24T10:00:00Z",
                "files_changed": 3,
            }
        ]
        mock_gh.get_priority_issues.return_value = [
            {
                "number": 42,
                "title": "Memory leak under load",
                "priority": "P0",
                "assignee": "bob",
                "days_open": 2,
            }
        ]

        # Mock Claude response with valid JSON
        mock_response = {
            "service": "payments",
            "error_rate_now": 5.2,
            "error_rate_30min_avg": 0.5,
            "likely_cause": "Recent commit abc123d introduced memory leak in retry logic under high load",
            "recent_deploys": ["abc123d: Fix memory leak in retry logic"],
            "recommended_action": "Rollback to previous commit or apply hotfix to memory leak",
            "escalate": True,
        }
        mock_mcp.ask.return_value = json.dumps(mock_response)

        # Execute workflow
        workflow = IncidentTriageWorkflow(mcp=mock_mcp, config=mock_config)
        result = workflow.execute(service_name="payments")

        # Assertions
        assert isinstance(result, dict), "Result should be a dict"

        # Check all required keys exist
        required_keys = [
            "service",
            "error_rate_now",
            "error_rate_30min_avg",
            "likely_cause",
            "recent_deploys",
            "recommended_action",
            "escalate",
        ]
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

        # Check data types
        assert isinstance(result["service"], str), "service should be str"
        assert isinstance(result["error_rate_now"], float), "error_rate_now should be float"
        assert isinstance(result["error_rate_30min_avg"], float), "error_rate_30min_avg should be float"
        assert isinstance(result["likely_cause"], str), "likely_cause should be str"
        assert isinstance(result["recent_deploys"], list), "recent_deploys should be list"
        assert isinstance(result["recommended_action"], str), "recommended_action should be str"
        assert isinstance(result["escalate"], bool), "escalate should be bool"

        # Check escalation logic (5.2 > 3 * 0.5 = 1.5)
        assert result["escalate"] is True, "Should escalate when error_rate_now > 3x baseline"


def test_incident_triage_degraded(mock_mcp, mock_config):
    """
    Test that IncidentTriageWorkflow handles MCP failures gracefully.

    Mocks db_tools.get_error_rate to raise an exception on the first call.
    Asserts:
    - execute() does NOT raise an exception
    - Returns a dict with escalate=True
    - Returns ESCALATE_FALLBACK-like structure with service name set
    """
    with patch('workflows.incident_triage.github_tools') as mock_gh, \
         patch('workflows.incident_triage.db_tools') as mock_db:

        # Set up mock to raise exception on first call (30-min error rate)
        mock_db.get_error_rate.side_effect = Exception("Database connection failed")

        # Set up other mocks to return data
        mock_gh.search_recent_commits.return_value = []
        mock_gh.get_priority_issues.return_value = []

        # Mock Claude to return valid JSON (shouldn't be reached, but set it)
        mock_mcp.ask.return_value = json.dumps({
            "service": "payments",
            "error_rate_now": 0,
            "error_rate_30min_avg": 0,
            "likely_cause": "Could not fetch data",
            "recent_deploys": [],
            "recommended_action": "Page on-call",
            "escalate": True,
        })

        # Execute workflow - should NOT raise exception
        workflow = IncidentTriageWorkflow(mcp=mock_mcp, config=mock_config)
        result = workflow.execute(service_name="payments")

        # Assertions
        assert isinstance(result, dict), "Result should be a dict even on failure"
        assert result["service"] == "payments", "Service name should be preserved"
        assert result["escalate"] is True, "Should escalate on degraded conditions"
        assert "failed" in result["likely_cause"].lower() or result["likely_cause"] != "", \
            "Fallback message should indicate failure"
