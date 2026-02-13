"""Register all MCP tools by importing their modules."""

from iterm2_agent.tools.read_screen import read_screen  # noqa: F401
from iterm2_agent.tools.run_command import run_command  # noqa: F401
from iterm2_agent.tools.send_text import send_text  # noqa: F401
from iterm2_agent.tools.send_control import send_control  # noqa: F401
from iterm2_agent.tools.watch_output import watch_output  # noqa: F401
from iterm2_agent.tools.manage_session import manage_session  # noqa: F401
