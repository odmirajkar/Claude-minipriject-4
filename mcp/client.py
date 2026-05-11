"""
MCP Client wrapper.

Wraps the Anthropic SDK to provide a clean interface for making
MCP tool calls in workflows. Handles authentication and connection lifecycle.

Students: Read this file, understand it, but do not modify it.
"""
from __future__ import annotations
import json
import anthropic
from typing import Any


class MCPClient:
    """
    Context manager that initialises MCP server connections and
    provides a simple interface for making tool calls.

    Usage:
        with MCPClient(config) as mcp:
            result = mcp.call("github_issues", {"repo": "owner/repo", "state": "open"})
    """

    def __init__(self, config):
        self.config = config
        self._client: anthropic.Anthropic | None = None

    def __enter__(self) -> "MCPClient":
        self._client = anthropic.Anthropic()
        return self

    def __exit__(self, *_):
        self._client = None

    def _mcp_servers(self) -> list[dict]:
        """Build the MCP server list from config."""
        servers = []
        if self.config.GITHUB_TOKEN:
            servers.append({
                "type": "url",
                "url": "https://api.github.com/mcp/sse",
                "name": "github-mcp",
                "authorization_token": self.config.GITHUB_TOKEN,
            })
        if self.config.PG_READ_URL:
            servers.append({
                "type": "url",
                "url": "https://mcp.postgres.io/sse",
                "name": "pg-mcp",
                "authorization_token": self.config.PG_READ_URL,
            })
        return servers

    def call(self, tool_name: str, tool_input: dict, model: str | None = None) -> Any:
        """
        Make a single MCP tool call and return the parsed result.

        Args:
            tool_name:  The MCP tool to call (e.g. 'github_issues')
            tool_input: Input parameters as a dict
            model:      Claude model to use (defaults to config.CLAUDE_MODEL)

        Returns:
            The parsed JSON result from the MCP tool, or None on error.

        Raises:
            RuntimeError: If client is not initialised (use as context manager)
        """
        if self._client is None:
            raise RuntimeError("MCPClient must be used as a context manager")

        model = model or self.config.CLAUDE_MODEL

        # Build a minimal prompt that tells Claude to call the specific tool
        prompt = (
            f"Call the {tool_name} tool with these exact parameters: "
            f"{json.dumps(tool_input)}. "
            f"Return only the tool result as-is."
        )

        response = self._client.beta.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            mcp_servers=self._mcp_servers(),
            betas=["mcp-client-2025-04-04"],
        )

        # Extract the MCP tool result from the response content
        for block in response.content:
            if getattr(block, "type", None) == "mcp_tool_result":
                raw = block.content[0].text if block.content else "{}"
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return raw
            if getattr(block, "type", None) == "text":
                # Claude returned text — try to parse as JSON
                try:
                    return json.loads(block.text)
                except json.JSONDecodeError:
                    return block.text

        return None

    def ask(self, prompt: str, model: str | None = None) -> str:
        """
        Send a prompt to Claude with MCP servers connected.
        Claude will decide which tools (if any) to call.

        Args:
            prompt: The full prompt text
            model:  Claude model to use

        Returns:
            Claude's text response as a string.
        """
        if self._client is None:
            raise RuntimeError("MCPClient must be used as a context manager")

        model = model or self.config.CLAUDE_MODEL

        response = self._client.beta.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            mcp_servers=self._mcp_servers(),
            betas=["mcp-client-2025-04-04"],
        )

        # Collect all text blocks
        text_parts = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)

        return "\n".join(text_parts)
