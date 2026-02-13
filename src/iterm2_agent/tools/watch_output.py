"""Tool: watch_output — Monitor terminal output for a pattern."""

from __future__ import annotations

import asyncio
import re

from fastmcp import Context

from iterm2_agent.connection import ITerm2Context, get_screen_lines
from iterm2_agent.server import mcp


@mcp.tool()
async def watch_output(
    ctx: Context,
    pattern: str,
    timeout: int = 60,
    session_id: str = "",
) -> str:
    """Monitor terminal output until a regex pattern is matched.

    Useful for waiting for a server to start, a build to complete,
    or a specific log message to appear.

    Args:
        pattern: Regular expression pattern to match against screen lines.
        timeout: Maximum seconds to wait before giving up.
        session_id: Target session ID. Empty string uses the current active session.

    Returns:
        The matched line(s) if found, or timeout notice with recent output.
    """
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        return f"Invalid regex pattern: {pattern!r} — {exc}"

    iterm_ctx: ITerm2Context = ctx.request_context.lifespan_context
    session = await iterm_ctx.resolve_session(session_id)

    deadline = asyncio.get_event_loop().time() + timeout

    async with session.get_screen_streamer() as streamer:
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break

            # Check current screen for pattern
            screen_lines, _, _ = await get_screen_lines(session)
            matched = [line for line in screen_lines if compiled.search(line)]
            if matched:
                return (
                    f"Pattern matched: {pattern!r}\n"
                    f"Matched lines ({len(matched)}):\n"
                    + "\n".join(matched)
                )

            # Wait for screen update
            try:
                wait_time = min(2.0, remaining)
                await asyncio.wait_for(streamer.async_get(), timeout=wait_time)
            except asyncio.TimeoutError:
                pass  # No update yet, loop and check again

    # Timeout — return last few lines for context
    screen_lines, _, _ = await get_screen_lines(session, max_lines=10)
    while screen_lines and not screen_lines[-1].strip():
        screen_lines.pop()

    recent = "\n".join(screen_lines[-5:]) if screen_lines else "(empty)"
    return (
        f"⏱️ Timed out after {timeout}s waiting for pattern: {pattern!r}\n\n"
        f"Last lines:\n{recent}"
    )
