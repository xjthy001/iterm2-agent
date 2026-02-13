"""Tool: run_command — Execute a command and wait for output."""

from __future__ import annotations

import asyncio

from fastmcp import Context

from iterm2_agent.connection import ITerm2Context, get_screen_lines
from iterm2_agent.security import SecurityGuard, SecurityLevel
from iterm2_agent.server import mcp


@mcp.tool()
async def run_command(
    ctx: Context,
    command: str,
    timeout: int = 30,
    session_id: str = "",
) -> str:
    """Execute a command in an iTerm2 session and return the output.

    Sends the command, waits for output to stabilize (no new output for 2s),
    then returns the new lines produced.

    Args:
        command: Shell command to execute.
        timeout: Maximum seconds to wait for command completion.
        session_id: Target session ID. Empty string uses the current active session.

    Returns:
        Command output text, plus security warnings if applicable.
    """
    # Security check
    level = SecurityGuard.check(command)
    warning = SecurityGuard.format_warning(command, level)

    iterm_ctx: ITerm2Context = ctx.request_context.lifespan_context
    session = await iterm_ctx.resolve_session(session_id)

    # Capture baseline screen state
    pre_contents = await session.async_get_screen_contents()
    baseline = (
        pre_contents.number_of_lines_above_screen
        + pre_contents.number_of_lines
    )

    # Send command with CR (not LF)
    await session.async_send_text(command + "\r")

    # Wait for output to stabilize using ScreenStreamer
    timed_out = False
    idle_count = 0
    max_idle = 2  # consecutive idle cycles before declaring "done"
    deadline = asyncio.get_event_loop().time() + timeout

    async with session.get_screen_streamer() as streamer:
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                timed_out = True
                break

            try:
                wait_time = min(1.0, remaining)
                await asyncio.wait_for(streamer.async_get(), timeout=wait_time)
                idle_count = 0  # New output received, reset idle counter
            except asyncio.TimeoutError:
                idle_count += 1
                if idle_count >= max_idle:
                    break  # Output has stabilized

    # Read final screen state
    post_contents = await session.async_get_screen_contents()
    post_total = (
        post_contents.number_of_lines_above_screen
        + post_contents.number_of_lines
    )

    # Extract new lines (those added after the command)
    new_line_count = post_total - baseline
    screen_lines, _, _ = await get_screen_lines(session)

    if new_line_count > 0 and new_line_count <= len(screen_lines):
        # Get only the newly added lines from the visible screen
        output_lines = screen_lines[-new_line_count:]
    else:
        # Fallback: return all visible lines
        output_lines = screen_lines

    # Strip trailing empty lines
    while output_lines and not output_lines[-1].strip():
        output_lines.pop()

    output = "\n".join(output_lines)

    parts = []
    if warning:
        parts.append(warning)
    parts.append(f"$ {command}")
    parts.append(output)
    if timed_out:
        parts.append(f"\n⏱️ Command timed out after {timeout}s (output may be incomplete)")

    return "\n".join(parts)
