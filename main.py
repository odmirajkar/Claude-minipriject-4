"""
FinTrack MCP Intelligence Platform — CLI entry point.

Usage:
    python main.py --check
    python main.py --workflow morning-brief
    python main.py --workflow incident-triage --service payments
"""
import argparse
import sys
import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import config
from mcp.client import MCPClient
from workflows.morning_brief import MorningBriefWorkflow
from workflows.incident_triage import IncidentTriageWorkflow

console = Console()


def cmd_check():
    """Verify all MCP server connections."""
    status = config.check()
    table = Table(title="MCP Server Status", show_header=True, header_style="bold blue")
    table.add_column("Server", style="bold")
    table.add_column("Status")
    for server, ok in status.items():
        icon = "[green]✓ Connected[/green]" if ok else "[red]✗ Missing token[/red]"
        table.add_row(server, icon)
    console.print(table)
    if not all(status[s] for s in ["github-mcp", "pg-mcp"]):
        console.print("[red]ERROR: github-mcp and pg-mcp are required. Check your .env file.[/red]")
        sys.exit(1)
    console.print("[green]Core connections OK — ready to run workflows.[/green]")


def cmd_morning_brief():
    """Run the Morning Intelligence Brief workflow (WF-01)."""
    console.print(Panel("[bold blue]WF-01: Morning Intelligence Brief[/bold blue]", expand=False))
    with MCPClient(config) as mcp:
        workflow = MorningBriefWorkflow(mcp=mcp, config=config)
        result = workflow.run()
    console.print(Panel(result, title="Morning Brief", border_style="blue"))


def cmd_incident_triage(service: str):
    """Run the Incident Triage workflow (WF-02)."""
    console.print(Panel(f"[bold red]WF-02: Incident Triage — {service}[/bold red]", expand=False))
    with MCPClient(config) as mcp:
        workflow = IncidentTriageWorkflow(mcp=mcp, config=config)
        result = workflow.run(service_name=service)
    console.print_json(json.dumps(result, indent=2))
    if result.get("escalate"):
        console.print("[bold red]⚠  ESCALATE TO ON-CALL[/bold red]")


def main():
    parser = argparse.ArgumentParser(description="FinTrack MCP Intelligence Platform")
    parser.add_argument("--check",    action="store_true",  help="Check MCP server connections")
    parser.add_argument("--workflow", choices=["morning-brief", "incident-triage"], help="Workflow to run")
    parser.add_argument("--service",  default="payments",   help="Service name (for incident-triage)")
    args = parser.parse_args()

    if args.check:
        cmd_check()
    elif args.workflow == "morning-brief":
        cmd_morning_brief()
    elif args.workflow == "incident-triage":
        cmd_incident_triage(args.service)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
