"""
Base workflow class — provided. Do not modify.

All workflows extend BaseWorkflow. The run() method provides logging,
timing, and error handling around your execute() implementation.

Students: Read this carefully — it shows the pattern your workflows must follow.
"""
from __future__ import annotations
import time
import traceback
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from mcp.client import MCPClient
    from config import Config

console = Console()


class BaseWorkflow(ABC):
    """
    Abstract base class for all FinTrack workflows.

    Subclasses must implement execute() and set the name class attribute.
    """
    name: str = "unnamed_workflow"

    def __init__(self, mcp: "MCPClient", config: "Config"):
        self.mcp = mcp
        self.config = config

    def run(self, **kwargs) -> Any:
        """
        Execute the workflow with timing and error handling.
        Calls self.execute(**kwargs) and returns its result.
        """
        console.print(f"[dim]Starting {self.name}...[/dim]")
        start = time.perf_counter()
        try:
            result = self.execute(**kwargs)
            elapsed = int((time.perf_counter() - start) * 1000)
            console.print(f"[dim]{self.name} completed in {elapsed}ms[/dim]")
            return result
        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            console.print(f"[red]{self.name} failed after {elapsed}ms: {exc}[/red]")
            traceback.print_exc()
            raise

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Implement the workflow logic here. Called by run()."""
        ...

    def _load_prompt(self, filename: str) -> str:
        """Load a prompt template from the prompts/ directory."""
        from pathlib import Path
        prompt_path = Path(__file__).parent.parent / "prompts" / filename
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_path}. "
                f"Create it as part of your task."
            )
        return prompt_path.read_text()
