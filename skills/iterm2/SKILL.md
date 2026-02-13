---
name: iterm2
description: Control iTerm2 terminal sessions — read the screen, run commands, send keystrokes, interact with TUIs, monitor output, and manage panes. Use when the user mentions iTerm2, terminal control, split pane, read screen, send keys, or session management. Triggers on "what's on my terminal", "run this in iTerm", "split the terminal", "stop the process", "monitor the output".
license: MIT
metadata:
  author: xjthy001
  version: "0.1.0"
---

# iTerm2 Terminal Control

Control iTerm2 sessions via the `iterm2-agent` MCP server. All tool names are prefixed with `mcp__iterm2-agent__`.

## Prerequisites

Before using any tool, verify both conditions are met:

### 1. iTerm2 must be running

- iTerm2 app must be open with at least one terminal window.
- The Python API must be enabled. Check: **iTerm2 → Settings → General → Magic → Enable Python API** (checkbox must be on).
- How to verify: if `mcp__iterm2-agent__read_screen` returns a connection error, iTerm2 is either not running or the Python API is disabled. Ask the user to:
  1. Open iTerm2
  2. Go to **iTerm2 → Settings → General → Magic**
  3. Check **Enable Python API**
  4. Restart Claude Code (the MCP server connects on startup)

### 2. The `iterm2-agent` MCP server must be installed and registered

The MCP server must be cloned, installed, and registered in `~/.claude.json`. How to check:

1. **Is the repo cloned and dependencies installed?** Look for the virtualenv at the clone path:
   ```bash
   ls /path/to/iterm2-agent/.venv/bin/python
   ```
   If missing, install:
   ```bash
   git clone git@github.com:xjthy001/iterm2-agent.git
   cd iterm2-agent
   uv venv && uv pip install -e .
   ```

2. **Is it registered in `~/.claude.json`?** The file must contain an `iterm2-agent` entry under `mcpServers`:
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
   Replace `/path/to/iterm2-agent` with the actual clone path. If `mcpServers` already has other entries, add `iterm2-agent` alongside them.

3. **Restart Claude Code** after editing `~/.claude.json` — the MCP server connects at session startup.

If a tool call fails with a connection error after both checks pass, ask the user to restart Claude Code.

## Core Principle: Read Before You Act

ALWAYS call `read_screen()` before taking action. This tells you:
- What program is running (shell prompt? TUI? server logs?)
- The session ID to target
- Whether the session is idle or busy

## Tool Reference

| Tool | Key Params | When to Use |
|------|-----------|-------------|
| `read_screen` | `lines` (int, default -1), `session_id` | First step in every workflow. See what's on screen. |
| `run_command` | `command` (str), `timeout` (int, default 30), `session_id` | Shell commands that produce output and finish (ls, git status, pytest). |
| `send_text` | `text` (str), `press_enter` (bool, default false), `session_id` | Interactive programs, REPLs, TUIs, or typing without executing. |
| `send_control` | `character` (str), `session_id` | Send Ctrl+key. Values: C, Z, D, L, ESCAPE, A, E, U, K, W, R. |
| `watch_output` | `pattern` (regex str), `timeout` (int, default 60), `session_id` | Wait for specific output (server ready, build complete, error). |
| `manage_session` | `action` (str), `session_id`, `direction` (str, default "horizontal") | Actions: list, create, split, close, focus. |

## Tool Selection Guide

| Scenario | Tools | Why |
|----------|-------|-----|
| Run a shell command | `run_command` | Sends command, waits for output to stabilize, returns result. |
| Start a server/long process | `send_text(text=cmd, press_enter=true)` then `watch_output(pattern=...)` | `run_command` would time out. Use `send_text` to launch, `watch_output` to confirm startup. |
| Interact with vim/nano/TUI | `send_text` + `send_control` | Precise keystroke control without auto-Enter. |
| REPL session (python, node) | `send_text(text=code, press_enter=true)` then `read_screen` | Send expressions one at a time, read results. |
| Stop a running process | `send_control(character="C")` | Sends Ctrl+C interrupt. |
| Multi-pane workflow | `manage_session(action="split")` then target panes by session_id | Split first, then run commands in specific panes. |

## Special Keys Reference

Keys sent via `send_control`:

| Key | `character` value | Action |
|-----|-------------------|--------|
| Ctrl+C | `C` | Interrupt process |
| Ctrl+Z | `Z` | Suspend process |
| Ctrl+D | `D` | EOF / exit shell |
| Ctrl+L | `L` | Clear screen |
| Escape | `ESCAPE` | Escape key |
| Ctrl+A | `A` | Beginning of line |
| Ctrl+E | `E` | End of line |
| Ctrl+U | `U` | Kill entire line |
| Ctrl+K | `K` | Kill to end of line |
| Ctrl+W | `W` | Kill previous word |
| Ctrl+R | `R` | Reverse history search |

Keys sent via `send_text` (escape sequences for TUI/REPL navigation):

| Key | `text` value | Use case |
|-----|-------------|----------|
| Up Arrow | `\x1b[A` | Navigate history, TUI menu up |
| Down Arrow | `\x1b[B` | TUI menu down |
| Right Arrow | `\x1b[C` | Cursor right |
| Left Arrow | `\x1b[D` | Cursor left |
| Tab | `\t` | Autocomplete |
| Enter (TUI) | `\r` | Submit in TUI (use `press_enter=true` instead for normal input) |
| Backspace | `\x7f` | Delete character |

Example — navigate a TUI menu down 3 items and select:
```
1. send_text(text="\x1b[B")     → down
2. send_text(text="\x1b[B")     → down
3. send_text(text="\x1b[B")     → down
4. send_text(text="\r")         → select
```

## iTerm2 Object Hierarchy

```
App → Window → Tab → Session (pane)
```

- **App**: The iTerm2 application. One per machine.
- **Window**: A visible window. Can contain multiple tabs.
- **Tab**: A tab within a window. Can contain multiple sessions (split panes).
- **Session**: A single terminal pane. This is what you interact with. Each session has a unique `session_id`.

When you call `manage_session(action="list")`, the returned list shows all sessions across all windows/tabs.

## Workflow Recipes

### 1. Run a command and get output
```
1. read_screen()                           → get session state
2. run_command(command="git status")       → execute and capture output
```

### 2. Start a dev server and verify it's running
```
1. read_screen()                                           → confirm shell is idle
2. send_text(text="npm run dev", press_enter=true)         → start server (don't wait)
3. watch_output(pattern="ready|listening|started", timeout=30)  → wait for ready signal
```

### 3. Split terminal and run tests in new pane
```
1. manage_session(action="split", direction="vertical")    → creates new pane, returns session_id
2. run_command(command="npm test", session_id="<new_id>")  → run tests in new pane
```

### 4. Stop a running process
```
1. read_screen()                        → see what's running
2. send_control(character="C")          → Ctrl+C to interrupt
3. read_screen()                        → verify process stopped
```

### 5. Interact with a REPL
```
1. run_command(command="python3")                          → launch REPL
2. send_text(text="import json", press_enter=true)         → send code
3. send_text(text="json.dumps({'a': 1})", press_enter=true)
4. read_screen()                                           → read output
5. send_control(character="D")                             → exit REPL (Ctrl+D)
```

### 6. Create a 4-pane dev layout
```
1. manage_session(action="split", direction="horizontal")  → bottom pane (id_B)
2. manage_session(action="split", direction="vertical")    → split original → right pane (id_C)
3. manage_session(action="split", direction="vertical", session_id=id_B) → bottom-right (id_D)
4. run_command(command="npm run dev", session_id=id_A)     → server (top-left)
5. run_command(command="npm test -- --watch", session_id=id_C) → tests (top-right)
6. send_text(text="tail -f logs/app.log", press_enter=true, session_id=id_B) → logs (bottom-left)
7. run_command(command="psql", session_id=id_D)            → database (bottom-right)
```

### 7. Multi-level cleanup (stop TUI / exit shell)
When a session is stuck in a TUI or process:
```
1. send_control(character="C")          → interrupt process
2. read_screen()                        → check state
3. send_text(text="q")                  → TUI quit key (if still in TUI)
4. read_screen()                        → check state
5. send_text(text="exit", press_enter=true) → exit shell/REPL
6. manage_session(action="close", session_id="...") → close pane if needed
```

## Session ID Guidance

- **Omit `session_id`** (or pass `""`) to target the currently active session. This is the default and works for single-pane workflows.
- **Use explicit `session_id`** when working with multiple panes. Get IDs from `manage_session(action="list")` or from the return value of `split`/`create`.
- Session IDs look like: `w0t0p0:A1B2C3D4-E5F6-...`

## Safety Rules

1. **Respect security warnings.** `run_command` classifies commands as SAFE, CAUTION, or DANGEROUS. If a DANGEROUS warning appears, confirm with the user before proceeding.
2. **Confirm destructive commands.** Before running `rm`, `sudo`, `kill`, `git push --force`, or similar — ask the user first.
3. **Verify after control characters.** After sending Ctrl+C/Z/D, always `read_screen()` to confirm the expected effect.
4. **Don't blindly retry.** If a command fails or times out, `read_screen()` to understand the current state before retrying.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No sessions found" | iTerm2 may not be running or has no open windows. Ask user to open iTerm2. |
| Command timed out | The command is still running. Use `read_screen()` to check, or `send_control(character="C")` to interrupt. |
| Wrong session targeted | Use `manage_session(action="list")` to see all sessions and their IDs. |
| Screen content looks stale | Call `read_screen()` again — screen updates are async. |
| Interactive prompt waiting | The program expects input. Use `send_text` to provide it, or `send_control(character="C")` to abort. |
| MCP server not connected | Check `~/.claude.json` has the `iterm2-agent` entry. Restart Claude Code. |
| Tool not found | The MCP server isn't registered or failed to start. Verify the virtualenv path in `~/.claude.json` is correct. |

## Debugging Tips

- **Always dump screen on unexpected results.** Call `read_screen()` after every failed or unclear operation.
- **Use `read_screen(lines=50)` for full context.** The default returns all visible lines, but specifying more can show scrollback.
- **Check for TUI artifacts.** Box-drawing characters (`┌─┐│└─┘`) indicate a TUI is still open — don't send shell commands.
- **Watch for shell prompts.** A line ending with `$` or `%` means the shell is idle and ready for commands.
- **Session IDs are stable.** A session ID doesn't change until the pane is closed. You can safely reuse IDs across multiple tool calls.

## Links

- [iTerm2 Python API documentation](https://iterm2.com/python-api/)
- [iterm2-agent GitHub repository](https://github.com/xjthy001/iterm2-agent)
