"""Tool: send_text — Send raw text to an iTerm2 session."""

from __future__ import annotations

import asyncio

from fastmcp import Context

from iterm2_agent.connection import ITerm2Context, get_screen_lines
from iterm2_agent.server import mcp


@mcp.tool()
async def send_text(
    ctx: Context,
    text: str,
    press_enter: bool = False,
    session_id: str = "",
) -> str:
    """Send text to an iTerm2 session without automatically pressing Enter.

    Use this for interactive programs, TUI interfaces, REPLs, or any scenario
    requiring precise input control. Set press_enter=True to submit the text.

    Args:
        text: The text to send.
        press_enter: Whether to press Enter (send CR) after the text.
        session_id: Target session ID. Empty string uses the current active session.

    Returns:
        Confirmation message with current screen state.
    """
    iterm_ctx: ITerm2Context = ctx.request_context.lifespan_context
    session = await iterm_ctx.resolve_session(session_id)

    await session.async_send_text(text)
    if press_enter:
        await session.async_send_text("\r")

    # Brief pause to let the terminal process the input
    await asyncio.sleep(0.5)

    screen_lines, _, _ = await get_screen_lines(session, max_lines=10)
    while screen_lines and not screen_lines[-1].strip():
        screen_lines.pop()

    preview = "\n".join(screen_lines[-5:]) if screen_lines else "(empty)"
    action = "sent + Enter" if press_enter else "sent (no Enter)"
    return f"Text {action}: {repr(text)}\n\nScreen (last lines):\n{preview}"
