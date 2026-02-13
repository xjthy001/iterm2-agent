# iterm2-agent

MCP server for controlling iTerm2 terminal sessions via the iTerm2 Python API.

Read the screen, run commands, send keystrokes, monitor output, and manage panes — all through [Model Context Protocol](https://modelcontextprotocol.io/).

## Prerequisites

- macOS with [iTerm2](https://iterm2.com/) installed
- iTerm2 Python API enabled: **Preferences → General → Magic → Enable Python API**
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`brew install uv`)

## Install

```bash
git clone git@github.com:xjthy001/iterm2-agent.git
cd iterm2-agent
uv venv
uv pip install -e .
```

## Tools

| Tool | Purpose |
|------|---------|
| `read_screen` | Read visible terminal content and cursor position |
| `run_command` | Execute a shell command, wait for output to stabilize, return result |
| `send_text` | Send raw text to a session (with optional Enter) |
| `send_control` | Send control characters (Ctrl+C, Ctrl+Z, Ctrl+D, etc.) |
| `watch_output` | Monitor output until a regex pattern matches |
| `manage_session` | List, create, split, close, or focus sessions |

### read_screen

Read the visible screen content of a session.

```
lines: int = -1          # Number of lines to read (-1 = all visible)
session_id: str = ""     # Target session (empty = active session)
```

### run_command

Execute a command and capture output. Waits for output to stabilize (2s idle) before returning.

```
command: str             # Shell command to execute
timeout: int = 30        # Max seconds to wait
session_id: str = ""
```

Commands are classified by a security guard:
- **SAFE** — read-only commands (`ls`, `pwd`, `git status`, ...)
- **CAUTION** — modifying commands (`mkdir`, `npm install`, `git push`, ...)
- **DANGEROUS** — destructive commands (`rm`, `sudo`, `kill`, ...) — produces a warning

### send_text

Send text to a session without automatically pressing Enter. Set `press_enter=true` to submit.

```
text: str                # Text to send
press_enter: bool = false
session_id: str = ""
```

### send_control

Send a control character.

```
character: str           # One of: C, Z, D, L, ESCAPE, A, E, U, K, W, R
session_id: str = ""
```

| Character | Key | Action |
|-----------|-----|--------|
| `C` | Ctrl+C | Interrupt |
| `Z` | Ctrl+Z | Suspend |
| `D` | Ctrl+D | EOF |
| `L` | Ctrl+L | Clear screen |
| `ESCAPE` | Esc | Escape |
| `A` | Ctrl+A | Beginning of line |
| `E` | Ctrl+E | End of line |
| `U` | Ctrl+U | Kill line |
| `K` | Ctrl+K | Kill to end of line |
| `W` | Ctrl+W | Kill word |
| `R` | Ctrl+R | Reverse search |

### watch_output

Block until a regex pattern appears on screen, or timeout.

```
pattern: str             # Regex pattern to match
timeout: int = 60        # Max seconds to wait
session_id: str = ""
```

### manage_session

Manage iTerm2 sessions.

```
action: str              # list | create | split | close | focus
session_id: str = ""     # Required for close/focus, optional for split
direction: str = "horizontal"  # horizontal | vertical (split only)
```

## Usage with Claude Code

### 1. Register the MCP server

Add the `iterm2-agent` entry to the `mcpServers` object in `~/.claude.json`:

```json
{
  "mcpServers": {
    "iterm2-agent": {
      "type": "stdio",
      "command": "/path/to/iterm2-agent/.venv/bin/python",
      "args": ["-m", "iterm2_agent"]
    }
  }
}
```

Replace `/path/to/iterm2-agent` with your actual clone path. The command must point to the Python binary inside the project's virtualenv so that dependencies are available.

> If `~/.claude.json` already has a `mcpServers` object, just add the `"iterm2-agent": { ... }` entry alongside existing servers. Don't overwrite the whole file.

Restart Claude Code after editing. The server connects to iTerm2 on startup — make sure iTerm2 is running and the Python API is enabled.

### 2. Install the Claude Code skill (optional)

The skill gives Claude a built-in reference for how to use the 6 tools effectively:

```bash
mkdir -p ~/.claude/skills/iterm2
cp skill/SKILL.md ~/.claude/skills/iterm2/SKILL.md
```

After installing, you can invoke it with `/iterm2` or it auto-activates when you mention terminal/iTerm2.

### 3. Verify

Start a new Claude Code session and try:

- "What's on my terminal right now?"
- "Run `git status` in iTerm2"
- "Split the terminal and run tests in the new pane"
- "Start the dev server and tell me when it's ready"
- "Send Ctrl+C to stop the running process"

## Architecture

```
┌─────────────────────────────────────┐
│         MCP Client                  │
│   (Claude Code / Claude Desktop)    │
└──────────────┬──────────────────────┘
               │ stdio (JSON-RPC)
┌──────────────▼──────────────────────┐
│       iterm2-agent (MCP Server)     │
│                                     │
│  server.py        FastMCP + lifespan│
│  connection.py    Session resolver  │
│  security.py      Command classifier│
│  tools/                             │
│    read_screen.py                   │
│    run_command.py                   │
│    send_text.py                     │
│    send_control.py                  │
│    watch_output.py                  │
│    manage_session.py                │
└──────────────┬──────────────────────┘
               │ WebSocket
┌──────────────▼──────────────────────┐
│         iTerm2 Python API           │
│     (iterm2.Connection)             │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│           iTerm2.app                │
└─────────────────────────────────────┘
```

## Project Structure

```
iterm2-agent/
├── pyproject.toml
├── config/
│   └── default.toml
├── src/iterm2_agent/
│   ├── __init__.py
│   ├── __main__.py           # Entry point: python -m iterm2_agent
│   ├── server.py             # FastMCP server with iTerm2 lifespan
│   ├── connection.py         # iTerm2Context, session resolution, screen reading
│   ├── security.py           # Command classification (SAFE/CAUTION/DANGEROUS)
│   └── tools/
│       ├── __init__.py       # Tool registration
│       ├── read_screen.py
│       ├── run_command.py
│       ├── send_text.py
│       ├── send_control.py
│       ├── watch_output.py
│       └── manage_session.py
├── tests/
│   ├── test_security.py      # Security guard unit tests
│   ├── test_read_screen.py   # Session resolution unit tests
│   ├── test_run_command.py   # Security integration tests
│   └── test_send_control.py  # Control character mapping tests
├── test_integration.py       # Live integration tests (requires iTerm2)
└── skill/
    └── SKILL.md              # Claude Code skill definition
```

## Testing

Unit tests (no iTerm2 required):

```bash
uv pip install pytest pytest-asyncio
uv run pytest
```

Live integration tests (requires iTerm2 running):

```bash
uv run python test_integration.py
```

## License

MIT
