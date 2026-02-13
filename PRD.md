# PRD: iTerm2 AI Agent — 基于 iTerm2 Python API 的终端智能代理

## 1. 概述

### 1.1 愿景

构建一个 AI Agent，通过 iTerm2 官方 Python API 与用户的真实终端会话进行深度交互。Agent 能够**实时监听终端输出、发送命令、理解上下文**，并基于 LLM 的推理能力自主完成终端操作任务。

与截图方案（视觉识别）不同，本方案直接获取**结构化文本数据**，延迟低、Token 消耗小、信息精确。

### 1.2 产品定位

```
用户场景：
"帮我在这个终端里部署一下这个项目"
"看看这个报错是什么原因，帮我修一下"
"监控这个服务的日志，出现 ERROR 就通知我"

Agent 行为：
1. 实时读取终端当前内容
2. 理解上下文（目录、环境、历史命令）
3. 执行命令并等待结果
4. 根据输出决定下一步操作
5. 循环直到任务完成或需要人工介入
```

### 1.3 与现有方案的差异

| 对比维度 | iterm-mcp (AppleScript) | 本方案 (Python API) |
|----------|------------------------|-------------------|
| 输出获取 | 轮询 `get contents` | **实时推送** `ScreenStreamer` |
| 滚动历史 | 仅可见区域 | 可访问完整历史 |
| 命令完成检测 | CPU 轮询 + 进程监控 | **Prompt Monitor** 精确回调 |
| 扩展能力 | 无 | 状态栏组件、自定义控制序列、RPC |
| 会话管理 | 单会话 | 多窗口/多 Tab/多 Pane |

---

## 2. 问题陈述

### 2.1 目标用户

- 开发者：希望 AI 辅助完成终端操作（部署、调试、日志分析）
- DevOps 工程师：自动化运维任务，监控异常
- 学习者：让 AI 解释终端输出，引导操作

### 2.2 核心痛点

1. **上下文断裂**：现有 AI 工具无法看到用户终端的实际状态
2. **手动复制粘贴**：用户需要手动复制终端输出给 AI
3. **无法持续监控**：AI 无法长时间观察终端变化
4. **操作不连贯**：AI 给出建议后，用户需手动执行，再手动反馈结果

---

## 3. 目标与非目标

### 3.1 目标 (Goals)

- **G1**: Agent 能实时获取 iTerm2 终端的文本输出（非截图）
- **G2**: Agent 能向终端发送命令和控制字符（Ctrl+C 等）
- **G3**: Agent 能精确检测命令执行完成（基于 Prompt Monitor）
- **G4**: Agent 能管理多个终端会话（创建/切换/关闭）
- **G5**: Agent 具备安全机制，危险命令需用户确认
- **G6**: 支持作为 MCP Server 对外暴露能力

### 3.2 非目标 (Non-Goals)

- 不做跨平台支持（仅 macOS + iTerm2）
- 不做终端 UI 渲染（不替代 iTerm2）
- 不做代码编辑（由其他工具负责）
- 不内置 LLM，仅提供终端交互能力层

---

## 4. 技术架构

### 4.1 整体架构

```
┌───────────────────────────────────────────────────┐
│                   MCP Client                       │
│          (Claude Desktop / Claude Code)            │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │              MCP Protocol (stdio)             │ │
│  └──────────────────┬───────────────────────────┘ │
└─────────────────────┼─────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────┐
│              iTerm2 Agent (MCP Server)             │
│                                                    │
│  ┌──────────────┐  ┌────────────┐  ┌───────────┐ │
│  │ Tool Router  │  │  Session   │  │ Security  │ │
│  │              │  │  Manager   │  │  Guard    │ │
│  └──────┬───────┘  └─────┬──────┘  └─────┬─────┘ │
│         │                │                │       │
│  ┌──────▼────────────────▼────────────────▼─────┐ │
│  │          iTerm2 Adapter Layer                 │ │
│  │                                               │ │
│  │  ┌─────────────┐  ┌────────────────────────┐ │ │
│  │  │ Output      │  │ Input                  │ │ │
│  │  │ Reader      │  │ Writer                 │ │ │
│  │  │             │  │                        │ │ │
│  │  │ • Screen    │  │ • async_send_text()    │ │ │
│  │  │   Streamer  │  │ • Control Characters   │ │ │
│  │  │ • Screen    │  │ • Custom Control Seq   │ │ │
│  │  │   Contents  │  │                        │ │ │
│  │  │ • Line Info │  │                        │ │ │
│  │  └─────────────┘  └────────────────────────┘ │ │
│  │                                               │ │
│  │  ┌─────────────┐  ┌────────────────────────┐ │ │
│  │  │ Monitors    │  │ Session Lifecycle      │ │ │
│  │  │             │  │                        │ │ │
│  │  │ • Prompt    │  │ • Create Window/Tab    │ │ │
│  │  │ • Focus     │  │ • Split Pane           │ │ │
│  │  │ • Custom    │  │ • Close Session        │ │ │
│  │  │   Control   │  │ • Set Variables        │ │ │
│  │  │   Sequence  │  │ • Set Profile          │ │ │
│  │  └─────────────┘  └────────────────────────┘ │ │
│  └───────────────────────────────────────────────┘ │
│                        │                           │
└────────────────────────┼───────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │  iTerm2 Python API  │
              │  (WebSocket 连接)    │
              │                     │
              │  iterm2.Connection  │
              │  .async_create()    │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │      iTerm2 App     │
              │   (终端模拟器进程)    │
              └─────────────────────┘
```

### 4.2 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 运行时 | Python 3.10+ | iTerm2 官方 API 仅支持 Python |
| iTerm2 交互 | `iterm2` 官方包 | 功能最全，实时推送，官方维护 |
| MCP 协议 | `mcp` Python SDK | 标准 MCP Server 实现 |
| 异步框架 | asyncio | iTerm2 API 全异步设计，天然契合 |
| 进程管理 | asyncio.Task | 多个 Monitor 并发运行 |
| 配置管理 | TOML / YAML | 安全规则、白名单等 |

### 4.3 连接生命周期

```
启动流程：
1. MCP Client 启动 Agent 进程（via stdio）
2. Agent 初始化 MCP Server
3. Agent 通过 iterm2.Connection.async_create() 连接 iTerm2
4. Agent 获取当前 App 状态（窗口、Tab、Session）
5. Agent 注册 ScreenStreamer、PromptMonitor 等监听器
6. Agent 向 MCP Client 注册可用 Tools
7. 等待 MCP Client 的 Tool 调用请求

关闭流程：
1. MCP Client 断开 stdio
2. Agent 取消所有 asyncio Tasks
3. Agent 关闭 iterm2.Connection
4. 进程退出
```

---

## 5. 核心功能设计

### 5.1 MCP Tools 定义

#### Tool 1: `read_screen`

读取当前终端屏幕内容。

```json
{
  "name": "read_screen",
  "description": "读取当前活跃 iTerm2 会话的屏幕内容",
  "inputSchema": {
    "type": "object",
    "properties": {
      "session_id": {
        "type": "string",
        "description": "目标会话 ID，为空则使用当前活跃会话"
      },
      "lines": {
        "type": "integer",
        "description": "读取的行数，默认读取整个可见区域",
        "default": -1
      },
      "include_cursor": {
        "type": "boolean",
        "description": "是否包含光标位置信息",
        "default": false
      }
    }
  }
}
```

**内部实现：**

```python
async def read_screen(session_id: str | None, lines: int, include_cursor: bool):
    session = await resolve_session(session_id)
    contents: iterm2.ScreenContents = await session.async_get_screen_contents()

    result_lines = []
    total = contents.number_of_lines
    start = max(0, total - lines) if lines > 0 else 0

    for i in range(start, total):
        line: iterm2.LineContents = contents.line(i)
        result_lines.append(line.string)

    result = {
        "text": "\n".join(result_lines),
        "total_lines": total,
        "lines_above_screen": contents.number_of_lines_above_screen
    }

    if include_cursor:
        result["cursor"] = {
            "x": contents.cursor_coord.x,
            "y": contents.cursor_coord.y
        }

    return result
```

---

#### Tool 2: `run_command`

在终端中执行命令并等待完成。

```json
{
  "name": "run_command",
  "description": "在 iTerm2 会话中执行命令，等待执行完成后返回输出",
  "inputSchema": {
    "type": "object",
    "properties": {
      "command": {
        "type": "string",
        "description": "要执行的命令"
      },
      "session_id": {
        "type": "string",
        "description": "目标会话 ID"
      },
      "timeout": {
        "type": "integer",
        "description": "超时时间（秒），默认 30",
        "default": 30
      },
      "wait_for_completion": {
        "type": "boolean",
        "description": "是否等待命令完成",
        "default": true
      }
    },
    "required": ["command"]
  }
}
```

**内部实现（核心 — 精确的命令完成检测）：**

```python
async def run_command(command: str, session_id: str | None, timeout: int):
    session = await resolve_session(session_id)

    # 1. 记录执行前的屏幕行数
    before = await session.async_get_screen_contents()
    before_lines = before.number_of_lines_above_screen + before.number_of_lines

    # 2. 发送命令
    await session.async_send_text(command + "\n")

    # 3. 等待命令完成 — 使用 ScreenStreamer 监听输出变化
    output_lines = []
    async with session.get_screen_streamer() as streamer:
        deadline = asyncio.get_event_loop().time() + timeout
        idle_count = 0

        while asyncio.get_event_loop().time() < deadline:
            try:
                contents = await asyncio.wait_for(
                    streamer.async_get(),
                    timeout=1.0
                )
                idle_count = 0  # 有新输出，重置空闲计数

                # 提取新增的输出行
                for i in range(contents.number_of_lines):
                    line = contents.line(i).string
                    output_lines.append(line)

            except asyncio.TimeoutError:
                idle_count += 1
                if idle_count >= 2:  # 连续 2 秒无新输出，认为完成
                    break

    # 4. 读取最终屏幕状态
    after = await session.async_get_screen_contents()

    return {
        "output": "\n".join(output_lines),
        "screen_snapshot": extract_screen_text(after),
        "completed": idle_count >= 2,
        "timed_out": idle_count < 2
    }
```

---

#### Tool 3: `send_control`

发送控制字符（Ctrl+C、Ctrl+Z 等）。

```json
{
  "name": "send_control",
  "description": "向终端发送控制字符",
  "inputSchema": {
    "type": "object",
    "properties": {
      "character": {
        "type": "string",
        "description": "控制字符：'C' = Ctrl+C, 'Z' = Ctrl+Z, 'D' = Ctrl+D, 'L' = Ctrl+L",
        "enum": ["C", "Z", "D", "L", "A", "E", "R"]
      },
      "session_id": {
        "type": "string"
      }
    },
    "required": ["character"]
  }
}
```

**内部实现：**

```python
CONTROL_CHARS = {
    "C": "\x03",  # SIGINT
    "Z": "\x1a",  # SIGTSTP
    "D": "\x04",  # EOF
    "L": "\x0c",  # Clear screen
    "A": "\x01",  # Home (行首)
    "E": "\x05",  # End (行尾)
    "R": "\x12",  # Reverse search
}

async def send_control(character: str, session_id: str | None):
    session = await resolve_session(session_id)
    ctrl = CONTROL_CHARS.get(character.upper())
    if ctrl is None:
        raise ValueError(f"Unsupported control character: {character}")
    await session.async_send_text(ctrl)
    return {"sent": f"Ctrl+{character.upper()}"}
```

---

#### Tool 4: `watch_output`

实时监控终端输出，当匹配到指定模式时通知。

```json
{
  "name": "watch_output",
  "description": "监控终端输出，匹配指定模式时返回",
  "inputSchema": {
    "type": "object",
    "properties": {
      "pattern": {
        "type": "string",
        "description": "正则表达式模式"
      },
      "timeout": {
        "type": "integer",
        "description": "最长等待时间（秒）",
        "default": 60
      },
      "session_id": {
        "type": "string"
      }
    },
    "required": ["pattern"]
  }
}
```

**内部实现（利用 ScreenStreamer 实时监听）：**

```python
import re

async def watch_output(pattern: str, timeout: int, session_id: str | None):
    session = await resolve_session(session_id)
    regex = re.compile(pattern)
    matched_lines = []

    async with session.get_screen_streamer() as streamer:
        deadline = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < deadline:
            try:
                contents = await asyncio.wait_for(
                    streamer.async_get(),
                    timeout=min(5.0, deadline - asyncio.get_event_loop().time())
                )
                for i in range(contents.number_of_lines):
                    line = contents.line(i).string
                    if regex.search(line):
                        matched_lines.append(line)

                if matched_lines:
                    return {
                        "matched": True,
                        "lines": matched_lines,
                        "pattern": pattern
                    }

            except asyncio.TimeoutError:
                continue

    return {
        "matched": False,
        "lines": [],
        "pattern": pattern,
        "timed_out": True
    }
```

---

#### Tool 5: `manage_session`

管理 iTerm2 会话（创建、列出、切换、关闭）。

```json
{
  "name": "manage_session",
  "description": "管理 iTerm2 终端会话",
  "inputSchema": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "enum": ["list", "create", "split", "close", "focus"],
        "description": "操作类型"
      },
      "session_id": {
        "type": "string",
        "description": "目标会话 ID（focus/close 时需要）"
      },
      "direction": {
        "type": "string",
        "enum": ["horizontal", "vertical"],
        "description": "分屏方向（split 时需要）"
      },
      "profile": {
        "type": "string",
        "description": "新会话使用的 iTerm2 Profile"
      }
    },
    "required": ["action"]
  }
}
```

**内部实现：**

```python
async def manage_session(action: str, **kwargs):
    app = await iterm2.async_get_app(connection)

    if action == "list":
        sessions = []
        for window in app.terminal_windows:
            for tab in window.tabs:
                for session in tab.sessions:
                    contents = await session.async_get_screen_contents()
                    last_line = contents.line(contents.number_of_lines - 1).string
                    sessions.append({
                        "session_id": session.session_id,
                        "name": await session.async_get_variable("name"),
                        "tty": await session.async_get_variable("tty"),
                        "last_line": last_line.strip(),
                        "grid_size": {
                            "cols": session.grid_size.width,
                            "rows": session.grid_size.height
                        }
                    })
        return {"sessions": sessions}

    elif action == "create":
        window = await iterm2.Window.async_create(connection)
        session = window.current_tab.current_session
        return {"session_id": session.session_id}

    elif action == "split":
        session = await resolve_session(kwargs.get("session_id"))
        vertical = kwargs.get("direction") == "vertical"
        new_session = await session.async_split_pane(vertical=vertical)
        return {"session_id": new_session.session_id}

    elif action == "close":
        session = await resolve_session(kwargs["session_id"])
        await session.async_close()
        return {"closed": True}

    elif action == "focus":
        session = await resolve_session(kwargs["session_id"])
        await session.async_activate()
        return {"focused": session.session_id}
```

---

#### Tool 6: `get_context`

获取终端环境上下文（当前目录、环境变量、Shell 类型等）。

```json
{
  "name": "get_context",
  "description": "获取当前终端会话的环境上下文信息",
  "inputSchema": {
    "type": "object",
    "properties": {
      "session_id": { "type": "string" }
    }
  }
}
```

**内部实现（利用 iTerm2 的 Shell Integration 变量）：**

```python
async def get_context(session_id: str | None):
    session = await resolve_session(session_id)

    # iTerm2 Shell Integration 自动填充这些变量
    context = {
        "path": await session.async_get_variable("path"),
        "hostname": await session.async_get_variable("hostname"),
        "username": await session.async_get_variable("user"),
        "shell": await session.async_get_variable("shell"),
        "terminal_size": {
            "cols": session.grid_size.width,
            "rows": session.grid_size.height
        },
        "tty": await session.async_get_variable("tty"),
        "pid": await session.async_get_variable("pid"),
        "job_name": await session.async_get_variable("jobName"),
        "command_line": await session.async_get_variable("commandLine"),
    }

    # 获取最近的屏幕快照作为额外上下文
    contents = await session.async_get_screen_contents()
    last_lines = []
    start = max(0, contents.number_of_lines - 5)
    for i in range(start, contents.number_of_lines):
        last_lines.append(contents.line(i).string)
    context["recent_output"] = "\n".join(last_lines)

    return context
```

---

### 5.2 高级特性

#### 5.2.1 Custom Control Sequence — 双向通信通道

利用 iTerm2 的自定义控制序列，在 Shell 脚本中主动向 Agent 发送事件：

```python
# Agent 端：注册监听器
async with iterm2.CustomControlSequenceMonitor(
    connection,
    "agent-secret-key",
    r'^(?P<event>\w+):(?P<data>.*)$'
) as monitor:
    while True:
        match = await monitor.async_get()
        event = match.group("event")
        data = match.group("data")
        await handle_shell_event(event, data)
```

```bash
# Shell 端：发送事件给 Agent
# 用户可以在脚本中嵌入这行来通知 Agent
printf "\033]1337;Custom=id=%s:%s\a" "agent-secret-key" "deploy_done:success"
```

使用场景：
- CI 脚本完成时通知 Agent
- 长时间任务的进度上报
- Shell 脚本请求 Agent 介入

#### 5.2.2 Status Bar 组件 — Agent 状态可视化

在 iTerm2 状态栏显示 Agent 状态：

```python
component = iterm2.StatusBarComponent(
    short_description="AI Agent",
    detailed_description="Shows AI Agent connection status",
    knobs=[],
    exemplar="[Agent: Ready]",
    update_cadence=None,
    identifier="com.iterm2-agent.status"
)

@iterm2.StatusBarRPC
async def status_callback(knobs):
    if agent.is_busy:
        return f"[Agent: {agent.current_task}]"
    return "[Agent: Ready]"

await component.async_register(connection, status_callback)
```

---

## 6. 安全设计

### 6.1 命令安全分级

```python
class CommandSafety:
    # 白名单：直接执行
    SAFE = {
        "ls", "pwd", "echo", "cat", "head", "tail", "grep",
        "wc", "date", "whoami", "env", "which", "file",
        "git status", "git log", "git diff", "git branch",
    }

    # 灰名单：需要 Agent 二次确认
    CAUTION = {
        "git commit", "git push", "git checkout",
        "npm install", "pip install", "brew install",
        "docker run", "docker stop",
        "mkdir", "cp", "mv", "touch",
    }

    # 黑名单：必须用户确认
    DANGEROUS = {
        "rm", "rmdir",
        "sudo", "su",
        "chmod", "chown",
        "kill", "pkill",
        "dd", "mkfs", "fdisk",
        "curl | sh", "wget | sh",
        "> /dev/", ">> /dev/",
    }
```

### 6.2 确认流程

```
Agent 想执行 "rm -rf node_modules" :

1. SecurityGuard 分类 → DANGEROUS
2. Agent 返回 MCP 响应：需要用户确认
3. MCP Client (Claude Desktop) 显示确认弹窗
4. 用户确认 → Agent 执行
5. 用户拒绝 → Agent 收到拒绝，调整策略
```

### 6.3 审计日志

```python
@dataclass(frozen=True)
class AuditEntry:
    timestamp: str
    session_id: str
    command: str
    safety_level: str
    user_confirmed: bool
    output_summary: str
```

所有命令执行均记录到本地审计日志文件（`~/.iterm2-agent/audit.log`）。

---

## 7. 数据流设计

### 7.1 命令执行完整流程

```
MCP Client                    Agent                     iTerm2 Python API          iTerm2 App
    │                           │                            │                        │
    │ CallTool(run_command,     │                            │                        │
    │   {command: "npm test"})  │                            │                        │
    │ ─────────────────────────>│                            │                        │
    │                           │                            │                        │
    │                           │ SecurityGuard.check()      │                        │
    │                           │ → CAUTION level            │                        │
    │                           │                            │                        │
    │                           │ async_get_screen_contents()│                        │
    │                           │ ──────────────────────────>│ get contents           │
    │                           │                            │ ──────────────────────> │
    │                           │                            │ <────── screen data ──  │
    │                           │ <── ScreenContents ────────│                        │
    │                           │                            │                        │
    │                           │ async_send_text("npm test")│                        │
    │                           │ ──────────────────────────>│ write text             │
    │                           │                            │ ──────────────────────> │
    │                           │                            │                        │ (执行命令)
    │                           │                            │                        │
    │                           │ ScreenStreamer.async_get() │                        │
    │                           │ ──────────────────────────>│                        │
    │                           │                            │ <── screen changed ──  │
    │                           │ <── ScreenContents ────────│                        │
    │                           │                            │                        │
    │                           │ (重复直到输出稳定)           │                        │
    │                           │                            │                        │
    │ <── {output: "...",       │                            │                        │
    │      completed: true} ────│                            │                        │
    │                           │                            │                        │
```

### 7.2 实时监控流程

```
Agent 后台 Task                  iTerm2 Python API          iTerm2 App
    │                                │                        │
    │  ScreenStreamer (长连接)        │                        │
    │ ─────────────────────────────> │                        │
    │                                │                        │
    │   (用户在终端中手动操作...)       │                        │
    │                                │ <── screen changed ──  │
    │ <── ScreenContents ────────────│                        │
    │                                │                        │
    │  检查是否匹配 watch 规则         │                        │
    │  如果匹配 → 触发回调             │                        │
    │  如果不匹配 → 继续等待           │                        │
    │                                │                        │
```

---

## 8. 配置设计

### 8.1 配置文件

路径：`~/.iterm2-agent/config.toml`

```toml
[server]
name = "iterm2-agent"
version = "0.1.0"

[security]
# 安全模式：strict (所有命令需确认) / normal / permissive
mode = "normal"

# 额外的安全命令白名单
safe_commands = ["cargo build", "go build", "make"]

# 额外的危险命令黑名单
dangerous_patterns = ["DROP TABLE", "TRUNCATE"]

# 允许 sudo
allow_sudo = false

[session]
# 默认读取行数
default_read_lines = 50

# 命令超时（秒）
default_timeout = 30

# 命令完成检测：空闲等待时间（秒）
idle_threshold = 2.0

[monitor]
# ScreenStreamer 轮询间隔（毫秒）— 仅在 streamer 不支持推送时使用
poll_interval_ms = 500

[audit]
# 审计日志
enabled = true
log_path = "~/.iterm2-agent/audit.log"
max_size_mb = 100
```

### 8.2 MCP Server 配置

Claude Desktop 配置 (`claude_desktop_config.json`)：

```json
{
  "mcpServers": {
    "iterm2-agent": {
      "command": "python",
      "args": ["-m", "iterm2_agent"],
      "env": {
        "ITERM2_AGENT_CONFIG": "~/.iterm2-agent/config.toml"
      }
    }
  }
}
```

---

## 9. 项目结构

```
iterm2-agent/
├── pyproject.toml               # 项目配置 & 依赖
├── README.md
├── src/
│   └── iterm2_agent/
│       ├── __init__.py
│       ├── __main__.py          # 入口：python -m iterm2_agent
│       ├── server.py            # MCP Server 主逻辑
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── read_screen.py   # Tool: read_screen
│       │   ├── run_command.py   # Tool: run_command
│       │   ├── send_control.py  # Tool: send_control
│       │   ├── watch_output.py  # Tool: watch_output
│       │   ├── manage_session.py # Tool: manage_session
│       │   └── get_context.py   # Tool: get_context
│       ├── adapter/
│       │   ├── __init__.py
│       │   ├── connection.py    # iTerm2 连接管理
│       │   ├── output_reader.py # 输出读取（ScreenStreamer 封装）
│       │   ├── input_writer.py  # 输入发送（send_text 封装）
│       │   └── session_manager.py # 会话生命周期管理
│       ├── security/
│       │   ├── __init__.py
│       │   ├── guard.py         # 命令安全检查
│       │   └── audit.py         # 审计日志
│       └── config.py            # 配置加载
├── tests/
│   ├── unit/
│   │   ├── test_read_screen.py
│   │   ├── test_run_command.py
│   │   ├── test_send_control.py
│   │   ├── test_security_guard.py
│   │   └── test_session_manager.py
│   └── e2e/
│       ├── test_basic_flow.py
│       └── test_multi_session.py
└── config/
    └── default.toml             # 默认配置
```

---

## 10. 里程碑

### Phase 1: 基础能力 (MVP)

- iTerm2 Python API 连接建立
- `read_screen` — 读取屏幕内容
- `run_command` — 执行命令 + 等待完成
- `send_control` — 控制字符
- MCP Server stdio 通信
- 基本安全检查

**交付物**: 可在 Claude Desktop 中使用的 MCP Server，支持基本的终端读写。

### Phase 2: 智能监控

- `watch_output` — 实时输出监控
- `get_context` — 环境上下文获取
- ScreenStreamer 实时推送集成
- 命令完成检测优化（结合 idle detection + prompt pattern）
- 审计日志系统

**交付物**: 支持长时间监控和精确命令完成检测。

### Phase 3: 多会话 & 高级特性

- `manage_session` — 多会话管理
- Custom Control Sequence 双向通信
- Status Bar 组件（Agent 状态可视化）
- 配置文件系统
- 完善的安全分级和确认流程

**交付物**: 完整的多会话 Agent，带可视化状态和双向通信。

### Phase 4: 生态集成

- 发布到 PyPI
- Smithery 一键安装支持
- Claude Code 集成（作为 MCP Server）
- 文档和示例
- 社区反馈迭代

**交付物**: 可公开发布的成熟产品。

---

## 11. 开放问题

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| 1 | iTerm2 Python API 需要用户手动开启（Preferences > Magic），如何降低配置门槛？ | 用户体验 | 首次运行时检测并引导开启 |
| 2 | ScreenStreamer 在高频输出时（如 `tail -f`）的性能表现如何？ | 可靠性 | Phase 2 进行压测，必要时增加防抖 |
| 3 | 命令完成检测的 idle 阈值如何自适应？编译命令可能有长时间无输出的阶段 | 准确性 | 结合 Shell Integration 的 prompt marker 做精确检测 |
| 4 | 多窗口场景下，如何确定 Agent 应该操作哪个会话？ | 用户体验 | 默认当前焦点会话 + 显式 session_id 指定 |
| 5 | 是否需要支持 iTerm2 的 tmux integration 模式？ | 兼容性 | Phase 3 评估，优先级低 |
| 6 | 安全规则是否需要支持正则匹配而非简单字符串？ | 安全性 | 是，Phase 2 实现 |

---

## 12. 附录：iTerm2 Python API 关键类参考

### ScreenContents

```python
class ScreenContents:
    number_of_lines: int                    # 屏幕总行数
    number_of_lines_above_screen: int       # 滚动历史行数
    cursor_coord: Point                     # 光标位置 (x, y)
    line(index: int) -> LineContents        # 获取指定行
```

### LineContents

```python
class LineContents:
    string: str                             # 行文本内容
    string_at(col: int) -> str              # 指定列的字符
    hard_eol: bool                          # 是否硬换行
```

### ScreenStreamer

```python
class ScreenStreamer:  # async context manager
    async async_get(style=False) -> ScreenContents | None
    # 阻塞直到屏幕内容变化，返回新内容
```

### Session 核心方法

```python
class Session:
    async async_send_text(text: str)                # 发送文本/命令
    async async_get_screen_contents() -> ScreenContents  # 获取屏幕
    async async_get_variable(name: str) -> Any       # 获取变量
    async async_set_variable(name: str, value: str)  # 设置变量
    async async_get_line_info() -> SessionLineInfo   # 行信息
    async async_get_profile() -> Profile             # 获取配置
    async async_split_pane(vertical=False) -> Session # 分屏
    async async_inject(data: bytes)                  # 注入原始数据
    async async_close()                              # 关闭会话
    async async_activate()                           # 激活会话
    get_screen_streamer(want_contents=True) -> ScreenStreamer  # 实时监听
```

### Connection

```python
# 建立连接
connection = await iterm2.Connection.async_create()

# 获取 App 实例
app = await iterm2.async_get_app(connection)

# 遍历所有会话
for window in app.terminal_windows:
    for tab in window.tabs:
        for session in tab.sessions:
            # ...
```
