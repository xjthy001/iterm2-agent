"""Tool: manage_session — Manage iTerm2 sessions."""

from __future__ import annotations

import iterm2
from fastmcp import Context

from iterm2_agent.connection import ITerm2Context
from iterm2_agent.server import mcp


@mcp.tool()
async def manage_session(
    ctx: Context,
    action: str,
    session_id: str = "",
    direction: str = "horizontal",
) -> str:
    """Manage iTerm2 terminal sessions.

    Args:
        action: One of 'list', 'create', 'split', 'close', 'focus'.
            - list: List all sessions across all windows and tabs.
            - create: Create a new terminal window.
            - split: Split the current/specified session.
            - close: Close the specified session.
            - focus: Bring the specified session into focus.
        session_id: Target session ID (required for close/focus, optional for split).
        direction: Split direction — 'horizontal' or 'vertical' (only for split).

    Returns:
        Result description or session listing.
    """
    iterm_ctx: ITerm2Context = ctx.request_context.lifespan_context

    if action == "list":
        return await _list_sessions(iterm_ctx)
    if action == "create":
        return await _create_window(iterm_ctx)
    if action == "split":
        return await _split_session(iterm_ctx, session_id, direction)
    if action == "close":
        return await _close_session(iterm_ctx, session_id)
    if action == "focus":
        return await _focus_session(iterm_ctx, session_id)

    return (
        f"Unknown action: {action!r}. "
        "Valid actions: list, create, split, close, focus"
    )


async def _list_sessions(ctx: ITerm2Context) -> str:
    """List all sessions with their IDs and last line of content."""
    lines = []
    for window in ctx.app.terminal_windows:
        for tab in window.tabs:
            for session in tab.sessions:
                contents = await session.async_get_screen_contents()
                # Find last non-empty line
                last_line = ""
                for i in range(contents.number_of_lines - 1, -1, -1):
                    text = contents.line(i).string.strip()
                    if text:
                        last_line = text
                        break

                lines.append(
                    f"  {session.session_id}  |  {last_line[:80]}"
                )

    if not lines:
        return "No sessions found."

    header = f"Sessions ({len(lines)}):\n"
    return header + "\n".join(lines)


async def _create_window(ctx: ITerm2Context) -> str:
    """Create a new iTerm2 window."""
    window = await iterm2.Window.async_create(ctx.connection)
    session = window.current_tab.current_session
    return f"Created new window. Session ID: {session.session_id}"


async def _split_session(
    ctx: ITerm2Context,
    session_id: str,
    direction: str,
) -> str:
    """Split a session horizontally or vertically."""
    session = await ctx.resolve_session(session_id)
    vertical = direction.lower() == "vertical"
    new_session = await session.async_split_pane(vertical=vertical)
    return (
        f"Split {'vertically' if vertical else 'horizontally'}. "
        f"New session ID: {new_session.session_id}"
    )


async def _close_session(ctx: ITerm2Context, session_id: str) -> str:
    """Close a specific session."""
    if not session_id:
        return "session_id is required for close action."
    session = await ctx.resolve_session(session_id)
    await session.async_close()
    return f"Closed session: {session_id}"


async def _focus_session(ctx: ITerm2Context, session_id: str) -> str:
    """Bring a session into focus."""
    if not session_id:
        return "session_id is required for focus action."
    session = await ctx.resolve_session(session_id)
    await session.async_activate()
    return f"Focused session: {session_id}"
