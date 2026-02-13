"""Entry point for iterm2-agent MCP server."""

from iterm2_agent.server import mcp
import iterm2_agent.tools  # noqa: F401 — registers all tools


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
