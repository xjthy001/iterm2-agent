"""iTerm2 connection management."""

from __future__ import annotations

from dataclasses import dataclass

import iterm2


@dataclass(frozen=True)
class ITerm2Context:
    """Immutable container for iTerm2 connection state."""

    connection: iterm2.Connection
    app: iterm2.App

    async def resolve_session(self, session_id: str = "") -> iterm2.Session:
        """Resolve a session by ID, or return the current active session."""
        if session_id:
            session = self.app.get_session_by_id(session_id)
            if session is None:
                raise ValueError(f"Session not found: {session_id}")
            return session

        session = self.app.current_terminal_window.current_tab.current_session
        if session is None:
            raise RuntimeError("No active iTerm2 session found")
        return session

    async def refresh_app(self) -> None:
        """Refresh the app state to pick up new windows/tabs/sessions."""
        # iterm2.App caches state; we need to re-fetch for accurate listings
        await self.app.async_refresh()


async def get_screen_lines(
    session: iterm2.Session,
    max_lines: int = -1,
) -> tuple[list[str], int, int]:
    """Read screen text from a session.

    Returns:
        (lines, cursor_x, cursor_y) where lines is a list of strings,
        and cursor_x/cursor_y are the cursor position.
    """
    contents = await session.async_get_screen_contents()
    total = contents.number_of_lines
    count = total if max_lines < 0 else min(max_lines, total)

    lines = [contents.line(i).string for i in range(count)]
    cursor_x = contents.cursor_coord.x
    cursor_y = contents.cursor_coord.y

    return lines, cursor_x, cursor_y
