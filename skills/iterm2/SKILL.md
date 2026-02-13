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

This skill requires the `iterm2-agent` MCP server to be installed and registered. See the [README](https://github.com/xjthy001/iterm2-agent) for setup instructions.

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
