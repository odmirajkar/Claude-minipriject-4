"""
MCP Audit Logger — TASK 1: Complete this file.

Every MCP tool call in this project must be logged here.
The log file is the governance record — treat it seriously.

Requirements:
  - Log file location: ~/.fintrack/audit.log
  - Format: JSONL (one JSON object per line)
  - Required fields: timestamp, workflow, tool, input_hash, status, duration_ms
  - Must NOT crash the caller if logging fails — log to stderr and continue
  - Log directory must be created if it does not exist

Do NOT log raw input values — hash them with SHA-256 for privacy.
"""
from __future__ import annotations
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


LOG_PATH = Path.home() / ".fintrack" / "audit.log"


class AuditLogger:
    """
    Logs MCP tool calls to a JSONL file.

    Usage:
        audit = AuditLogger()
        audit.log(
            workflow="morning_brief",
            tool="github_issues",
            tool_input={"repo": "owner/repo"},
            status="success",
            duration_ms=342,
        )
    """

    def __init__(self, log_path: Path = LOG_PATH):
        self.log_path = log_path

    def log(
        self,
        workflow: str,
        tool: str,
        tool_input: dict,
        status: str,
        duration_ms: int,
    ) -> None:
        """
        Write one audit log entry.

        TASK 1: Implement this method.

        Args:
            workflow:    Name of the workflow making the call (e.g. 'morning_brief')
            tool:        MCP tool name (e.g. 'github_issues')
            tool_input:  The dict passed to the tool
            status:      'success' or 'error'
            duration_ms: Wall-clock milliseconds the tool call took
        """
        # TODO: Build the log entry dict with all required fields.
        #       Hash tool_input with SHA-256 — store the hex digest, not the raw value.
        #       Create the log directory if it doesn't exist.
        #       Append the entry as a JSON line to self.log_path.
        #       If any I/O error occurs: print a warning to sys.stderr and return — do NOT raise.
        raise NotImplementedError("Task 1: implement AuditLogger.log()")

    @staticmethod
    def _hash_input(tool_input: dict) -> str:
        """Return the SHA-256 hex digest of the JSON-serialised input."""
        # TODO: Implement this.
        #       Serialise tool_input to a JSON string (sorted keys for determinism),
        #       encode to bytes, and return the SHA-256 hex digest.
        raise NotImplementedError("Task 1: implement _hash_input()")

    def recent(self, n: int = 20) -> list[dict]:
        """Return the last n log entries as a list of dicts."""
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text().strip().splitlines()
        entries = []
        for line in lines[-n:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return entries
