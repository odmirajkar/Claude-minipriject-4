# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Purpose

FinTrack is an MCP-powered engineering intelligence platform that connects to live business data via GitHub and PostgreSQL servers to deliver operational insights. It enables engineering teams to quickly understand what needs attention through two automated workflows: a daily morning intelligence brief summarizing open PRs and priority issues, and live incident triage that diagnoses the probable cause of service disruptions and recommends escalation decisions.

## Quick Start

```bash
# Activate the virtual environment
source venv/bin/activate

# Check MCP server connections
python main.py --check

# Run the Morning Intelligence Brief workflow
python main.py --workflow morning-brief

# Run incident triage for a specific service
python main.py --workflow incident-triage --service payments

# Run tests
pytest tests/ -v
pytest tests/test_github_tools.py::test_get_open_prs -v  # single test
```

## Architecture

### High-Level Flow

1. **CLI Entry (main.py)** → parses arguments and routes to workflow commands
2. **MCPClient (mcp/client.py)** → context manager that wraps Anthropic SDK to connect to MCP servers
3. **Workflows (workflows/*.py)** → extend BaseWorkflow, implement execute() method, orchestrate data gathering and Claude reasoning
4. **Tool Wrappers (mcp/github_tools.py, mcp/db_tools.py)** → handle MCP tool calls, error handling, and logging
5. **Audit Logger (mcp/audit.py)** → logs all tool calls to ~/.fintrack/audit.log in JSONL format

### Key Components

**MCPClient (mcp/client.py)**
- Context manager that initializes Anthropic SDK with MCP server connections
- Two main methods:
  - `call(tool_name, tool_input)` → makes a direct MCP tool call, returns parsed JSON
  - `ask(prompt)` → sends a prompt to Claude with MCP servers connected, Claude decides which tools to call
- Automatically constructs the MCP server list from config environment variables
- Handles response parsing (extracts text or tool results from Claude's response)

**BaseWorkflow (workflows/base.py)**
- Abstract base class all workflows extend
- `run()` method provides timing, logging, and error handling around your execute() implementation
- `execute(**kwargs)` method that subclasses must implement — this is where business logic lives
- Helper method `_load_prompt(filename)` loads prompt templates from prompts/ directory
- Subclasses must set the `name` class attribute

**Workflow Implementations (workflows/morning_brief.py, workflows/incident_triage.py)**
- WF-01 (Morning Brief): Fetches open PRs, priority issues, and overnight DB alerts; uses Claude to synthesize into a markdown brief with specific section headers
- WF-02 (Incident Triage): Fetches error rates, recent commits, and open bugs; uses Claude to infer probable cause and return a JSON report with escalation decision

**Tool Wrappers (mcp/github_tools.py, mcp/db_tools.py)**
- github_tools: `get_open_prs()`, `get_priority_issues()`, `search_recent_commits()`
- db_tools: `get_overnight_alerts()`, `get_error_rate()` (simulated data in lab)
- All tool wrapper functions:
  - Accept MCPClient and parameters
  - Call mcp.call() with appropriate tool_name and tool_input
  - Log each call via AuditLogger
  - Return structured dicts or lists of dicts (not raw API responses)
  - Return [] on error, never raise exceptions (caller should never see MCP exceptions)

**Audit Logger (mcp/audit.py)**
- Logs every MCP tool call to ~/.fintrack/audit.log (JSONL format)
- Required fields: timestamp, workflow, tool, input_hash, status, duration_ms
- Hashes tool input with SHA-256 for privacy (never logs raw values)
- Non-blocking: if logging fails, prints warning to stderr and continues

**Configuration (config.py)**
- Loads from environment variables (all prefixed with FINTRACK_)
- Keys: GITHUB_TOKEN, PG_READ_URL, JIRA_TOKEN, JIRA_BASE_URL, SLACK_WEBHOOK, GITHUB_REPO, CLAUDE_MODEL
- `check()` method returns dict of which servers are configured

### Data Flow Example: Morning Brief Workflow

1. User runs: `python main.py --workflow morning-brief`
2. main.py calls MorningBriefWorkflow.run()
3. BaseWorkflow.run() calls MorningBriefWorkflow.execute()
4. execute() method:
   - Calls github_tools.get_open_prs() → calls mcp.call("github_pull_requests", ...) → AuditLogger logs it
   - Calls github_tools.get_priority_issues() → same pattern
   - Calls db_tools.get_overnight_alerts()
   - Loads morning_brief.txt prompt template
   - Injects data into prompt (replacing {{PR_DATA}}, {{ISSUE_DATA}}, {{DB_ALERTS}})
   - Calls mcp.ask(prompt) → Claude reasons over data and MCP servers
   - Returns markdown string with required section headers
5. main.py displays result in a panel

## Architecture Rules

1. **All tokens via environment variables only** — NEVER hardcode credentials. Config.py loads from environment.
2. **Every MCP tool call must be logged via AuditLogger** — workflows use tool wrappers that log automatically; if adding new calls, ensure audit.log() is called.
3. **No PII flows through any prompt** — use aggregated data only. Examples: "3 open P0 issues" not "John's issue"; "error rate: 2.5/sec" not raw error samples with customer names.
4. **Tool wrappers never raise exceptions** — they handle errors gracefully, log, and return empty data structures. This allows workflows to continue gracefully if one data source fails.
5. **Workflows extend BaseWorkflow** — implement execute() method, use mcp.ask() for Claude reasoning, load prompt templates with _load_prompt().
6. **Input hashing for audit privacy** — all MCP tool inputs are hashed with SHA-256 before logging. Never log raw parameter values (API keys, URLs, queries) to the audit log.
7. **Graceful degradation on MCP failures** — if any MCP server is unavailable or a tool call fails, the workflow must continue with empty/simulated data rather than crashing. The audit log captures all failures for later investigation.

## Common Development Tasks

### Running Workflows

```bash
# Check that MCP servers are properly configured
python main.py --check

# Morning Intelligence Brief
python main.py --workflow morning-brief

# Incident Triage for a service
python main.py --workflow incident-triage --service payments
python main.py --workflow incident-triage --service orders
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_github_tools.py -v

# Run a single test
pytest tests/test_github_tools.py::test_get_open_prs -v

# Run with output capture disabled (see print() statements)
pytest tests/ -v -s
```

### Adding a New Workflow

1. Create workflows/my_workflow.py extending BaseWorkflow
2. Set the `name` class attribute
3. Implement execute() method that:
   - Calls tool wrappers to fetch data
   - Loads a prompt template with _load_prompt("my_prompt.txt")
   - Calls self.mcp.ask(prompt) with injected data
   - Returns the result (string or dict depending on workflow)
4. Create prompts/my_prompt.txt with your Claude instructions
5. Wire into main.py with a new argparse choice

### Adding a New GitHub MCP Tool Wrapper

1. In mcp/github_tools.py, create a function like:
   ```python
   def my_tool(mcp: "MCPClient", repo: str, **kwargs) -> list[dict]:
       start = time.time()
       try:
           result = mcp.call("github_tool_name", {"repo": repo, ...})
           _audit.log(workflow="<current>", tool="github_tool_name", tool_input={...}, status="success", duration_ms=...)
           return result
       except Exception as e:
           _audit.log(..., status="error", ...)
           return []
   ```
2. The tool wrapper handles error logging and returns [] on failure

### Checking Recent Audit Logs

```python
from mcp.audit import AuditLogger
audit = AuditLogger()
recent_calls = audit.recent(n=20)
for entry in recent_calls:
    print(entry)  # Each entry is a dict with timestamp, workflow, tool, input_hash, status, duration_ms
```

## MCP Server Registry

| Server  | Purpose                | Environment Variable | Required |
|---------|------------------------|----------------------|----------|
| github  | PR, issue, commit data | FINTRACK_GITHUB_TOKEN | Yes (WF-01, WF-02) |
| pg      | Error rates, DB alerts | FINTRACK_PG_READ_URL | Yes (WF-01, WF-02) |
| jira    | Ticket data (optional) | FINTRACK_JIRA_TOKEN | No |
| slack   | Notifications (future) | FINTRACK_SLACK_WEBHOOK | No |

## Workflow Specifications

### WF-01: Morning Intelligence Brief

**Trigger:** `python main.py --workflow morning-brief`

**MCP Tools Called (in order):**
1. `github_pull_requests` → fetches open PRs
2. `github_issues` → fetches open P0/P1 issues
3. (db_tools.get_overnight_alerts simulated)

**Output:** Markdown string with EXACTLY these section headers:
- `## PRs_NEEDING_REVIEW`
- `## OPEN_P0_P1`
- `## OVERNIGHT_DB_ALERTS`
- `## ACTION_ITEMS` (exactly 3 bullet points, most urgent first)

If any data source returns empty, include the section header with "No data returned from [source]"

**Constraints:** No PII, no raw SQL, no customer names

### WF-02: Incident Triage

**Trigger:** `python main.py --workflow incident-triage --service <name>`

**MCP Tools Called (in order):**
1. `get_error_rate(service, window_minutes=30)`
2. `search_recent_commits(repo, service, hours=4)`
3. `get_priority_issues(repo, labels=["bug", service])`
4. `get_error_rate(service, window_minutes=5)`

**Output:** JSON object matching IncidentReport schema:
```json
{
  "service": "string",
  "error_rate_now": "float (errors/second, last 5 min)",
  "error_rate_30min_avg": "float (errors/second, 30 min avg)",
  "likely_cause": "string (1-2 sentences, Claude's inference)",
  "recent_deploys": ["list of 'sha: message' strings"],
  "recommended_action": "string (specific next step)",
  "escalate": "bool (true if error_rate_now > 3x error_rate_30min_avg)"
}
```

**Error Handling:** If any tool call fails, log to stderr, use empty data, continue. If Claude returns invalid JSON, log to stderr and return ESCALATE_FALLBACK with service name set.

## Environment Variables

All prefixed with `FINTRACK_`:

```bash
FINTRACK_GITHUB_TOKEN="ghp_xxxxx"                    # GitHub PAT
FINTRACK_PG_READ_URL="postgresql://user:pass@host"   # DB read replica
FINTRACK_JIRA_TOKEN="jira_token"                      # Jira API token (optional)
FINTRACK_JIRA_BASE_URL="https://company.atlassian.net"
FINTRACK_SLACK_WEBHOOK="https://hooks.slack.com/..."  # Slack webhook (optional)
FINTRACK_GITHUB_REPO="instructor/fintrack-backend-lab" # Default repo
CLAUDE_MODEL="claude-sonnet-4-20250514"                # Claude model to use
```

## Testing

All tests are in tests/ directory. Use pytest.

**Test Files:**
- test_audit.py → AuditLogger functionality
- test_github_tools.py → Tool wrapper behavior
- test_workflows.py → Workflow execution

**Key Testing Pattern:**
- Mock MCPClient.call() to return simulated data
- Call tool wrapper or workflow with mock MCP
- Assert correct data structures and logging

## File Structure

```
fintrack-mcp-intel/
├── main.py                       # CLI entry point
├── config.py                     # Config from env vars
├── requirements.txt              # Dependencies
├── CLAUDE.md                     # This file
├── README.md                     # User-facing docs
├── mcp/
│   ├── client.py                 # MCPClient context manager (read-only)
│   ├── github_tools.py           # GitHub MCP tool wrappers (implement)
│   ├── db_tools.py               # PostgreSQL tool wrappers (provided, simulated)
│   └── audit.py                  # Audit logger (implement)
├── workflows/
│   ├── base.py                   # BaseWorkflow abstract class (read-only)
│   ├── morning_brief.py          # WF-01 implementation (implement)
│   └── incident_triage.py        # WF-02 implementation (implement)
├── prompts/
│   ├── morning_brief.txt         # WF-01 Claude prompt (write)
│   └── incident_triage.txt       # WF-02 Claude prompt (write)
└── tests/
    ├── test_audit.py
    ├── test_github_tools.py
    └── test_workflows.py
```

## Prompt Templates

All prompts are Claude instructions that guide the LLM to synthesize operational data into structured outputs.

### WF-01: Morning Intelligence Brief
- **File:** `prompts/morning_brief.txt`
- **Purpose:** Synthesize PR, issue, and alert data into a markdown brief with 4 required sections
- **Output:** Markdown with section headers: PRs_NEEDING_REVIEW, OPEN_P0_P1, OVERNIGHT_DB_ALERTS, ACTION_ITEMS
- **Key Instruction:** Return EXACTLY 3 action items, ordered by urgency; handle empty data with "No data returned from [source]" message

### WF-02: Incident Triage
- **File:** `prompts/incident_triage.txt`
- **Purpose:** Analyze error rates, recent commits, and open bugs to determine root cause and escalation
- **Output:** JSON object with service, error rates, likely_cause, recent_deploys, recommended_action, escalate flag
- **Key Instruction:** Return ONLY valid JSON (no preamble); escalate=true if error_rate_now > 3× error_rate_30min_avg

## References

- GitHub MCP Server: https://github.com/modelcontextprotocol/servers/tree/main/src/github
- PostgreSQL MCP Server: https://github.com/modelcontextprotocol/servers/tree/main/src/postgres
- Anthropic Python SDK: https://github.com/anthropics/anthropic-sdk-python
- MCP Documentation: https://modelcontextprotocol.io
