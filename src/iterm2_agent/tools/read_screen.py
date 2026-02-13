"""Tool: read_screen — Read iTerm2 terminal screen contents."""

from __future__ import annotations

from fastmcp import Context

from iterm2_agent.connection import ITerm2Context, get_screen_lines
from iterm2_agent.server import mcp


@mcp.tool()
async def read_screen(
    ctx: Context,
    lines: int = -1,
    session_id: str = "",
) -> str:
    """Read the screen contents of an iTerm2 session.

    Args:
        lines: Number of lines to read. -1 means all visible lines.
        session_id: Target session ID. Empty string uses the current active session.

    Returns:
        Screen text with cursor position and line count metadata.
    """
    iterm_ctx: ITerm2Context = ctx.request_context.lifespan_context
    session = await iterm_ctx.resolve_session(session_id)
    screen_lines, cursor_x, cursor_y = await get_screen_lines(session, lines)

    # Strip trailing empty lines for cleaner output
    while screen_lines and not screen_lines[-1].strip():
        screen_lines.pop()

    text = "\n".join(screen_lines)
    return (
        f"Session: {session.session_id}\n"
        f"Cursor: line {cursor_y}, column {cursor_x}\n"
        f"Lines: {len(screen_lines)}\n"
        f"---\n{text}"
    )
