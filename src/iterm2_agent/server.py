"""FastMCP Server definition with iTerm2 lifespan management."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import iterm2
from fastmcp import FastMCP

from iterm2_agent.connection import ITerm2Context


@asynccontextmanager
async def iterm2_lifespan(server: FastMCP) -> AsyncIterator[ITerm2Context]:
    """Manage iTerm2 connection lifecycle.

    Connects on startup, yields the context for tools to use,
    and ensures cleanup on shutdown.
    """
    connection = await iterm2.Connection.async_create()
    app = await iterm2.async_get_app(connection)
    ctx = ITerm2Context(connection=connection, app=app)
    try:
        yield ctx
    finally:
        # iterm2 library handles its own cleanup on GC
        pass


mcp = FastMCP(
    name="iterm2-agent",
    instructions=(
        "Control iTerm2 terminal sessions. You can read screen contents, "
        "execute commands, send text and control characters, monitor output, "
        "and manage sessions (list, create, split, close, focus)."
    ),
    version="0.1.0",
    lifespan=iterm2_lifespan,
)
