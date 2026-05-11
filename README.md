# FinTrack MCP Engineering Intelligence Platform

A Claude Code-powered operational intelligence tool that connects to live
business data via MCP and answers engineering questions in natural language.

## Quick Start

```bash
# 1. Clone and set up
git clone https://github.com/instructor/fintrack-mcp-intel
cd fintrack-mcp-intel
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your GitHub PAT and DB URL

# 3. Verify connections
python main.py --check

# 4. Run a workflow
python main.py --workflow morning-brief
python main.py --workflow incident-triage --service payments
```

## Project Structure

See CLAUDE.md for architecture documentation (you will write this in Task 5).

## Workflows

| ID    | Command                                      | Description                    |
|-------|----------------------------------------------|--------------------------------|
| WF-01 | `--workflow morning-brief`                   | Daily engineering brief        |
| WF-02 | `--workflow incident-triage --service NAME`  | Live incident investigation    |

## Running Tests

```bash
pytest tests/ -v
```
