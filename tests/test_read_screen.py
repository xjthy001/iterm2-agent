"""Tests for read_screen — requires mocking iTerm2 API."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from iterm2_agent.connection import ITerm2Context


class TestResolveSession:
    @pytest.fixture
    def mock_ctx(self):
        """Create a mock ITerm2Context."""
        ctx = MagicMock(spec=ITerm2Context)
        ctx.resolve_session = AsyncMock()
        return ctx

    @pytest.mark.asyncio
    async def test_resolve_with_empty_id_returns_active(self, mock_ctx):
        mock_session = MagicMock()
        mock_session.session_id = "w0t0p0"

        # Create a real ITerm2Context with mocked internals
        app = MagicMock()
        app.current_terminal_window.current_tab.current_session = mock_session
        app.get_session_by_id.return_value = None

        connection = MagicMock()
        ctx = ITerm2Context(connection=connection, app=app)

        session = await ctx.resolve_session("")
        assert session.session_id == "w0t0p0"

    @pytest.mark.asyncio
    async def test_resolve_with_valid_id(self):
        mock_session = MagicMock()
        mock_session.session_id = "w1t0p0"

        app = MagicMock()
        app.get_session_by_id.return_value = mock_session

        connection = MagicMock()
        ctx = ITerm2Context(connection=connection, app=app)

        session = await ctx.resolve_session("w1t0p0")
        assert session.session_id == "w1t0p0"
        app.get_session_by_id.assert_called_once_with("w1t0p0")

    @pytest.mark.asyncio
    async def test_resolve_with_invalid_id_raises(self):
        app = MagicMock()
        app.get_session_by_id.return_value = None

        connection = MagicMock()
        ctx = ITerm2Context(connection=connection, app=app)

        with pytest.raises(ValueError, match="Session not found"):
            await ctx.resolve_session("nonexistent")
