"""Tool: send_control — Send control characters to an iTerm2 session."""

from __future__ import annotations

import asyncio

from fastmcp import Context

from iterm2_agent.connection import ITerm2Context, get_screen_lines
from iterm2_agent.server import mcp

CONTROL_MAP: dict[str, str] = {
    "C": "\x03",       # Ctrl+C — interrupt
    "Z": "\x1a",       # Ctrl+Z — suspend
    "D": "\x04",       # Ctrl+D — EOF
    "L": "\x0c",       # Ctrl+L — clear screen
    "ESCAPE": "\x1b",  # Escape key
    "A": "\x01",       # Ctrl+A — beginning of line
    "E": "\x05",       # Ctrl+E — end of line
    "U": "\x15",       # Ctrl+U — kill line
    "K": "\x0b",       # Ctrl+K — kill to end of line
    "W": "\x17",       # Ctrl+W — kill word
    "R": "\x12",       # Ctrl+R — reverse search
}


@mcp.tool()
async def send_control(
    ctx: Context,
    character: str,
    session_id: str = "",
) -> str:
    """Send a control character to an iTerm2 session.

    Args:
        character: Control character name. One of:
            'C' (Ctrl+C interrupt), 'Z' (Ctrl+Z suspend), 'D' (Ctrl+D EOF),
            'L' (Ctrl+L clear), 'ESCAPE', 'A' (beginning of line),
            'E' (end of line), 'U' (kill line), 'K' (kill to end),
            'W' (kill word), 'R' (reverse search).
        session_id: Target session ID. Empty string uses the current active session.

    Returns:
        Confirmation with current screen state.
    """
    key = character.upper()
    ctrl_char = CONTROL_MAP.get(key)
    if ctrl_char is None:
        valid = ", ".join(sorted(CONTROL_MAP.keys()))
        return f"Invalid control character: {character!r}. Valid options: {valid}"

    iterm_ctx: ITerm2Context = ctx.request_context.lifespan_context
    session = await iterm_ctx.resolve_session(session_id)

    await session.async_send_text(ctrl_char)
    await asyncio.sleep(0.5)

    screen_lines, _, _ = await get_screen_lines(session, max_lines=10)
    while screen_lines and not screen_lines[-1].strip():
        screen_lines.pop()

    preview = "\n".join(screen_lines[-5:]) if screen_lines else "(empty)"
    label = f"Ctrl+{key}" if key != "ESCAPE" else "Escape"
    return f"Sent: {label}\n\nScreen (last lines):\n{preview}"
