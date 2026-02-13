"""Tests for run_command — security integration."""

from iterm2_agent.security import SecurityGuard, SecurityLevel


class TestRunCommandSecurity:
    """Test that run_command's security checks work correctly."""

    def test_safe_command_no_warning(self):
        level = SecurityGuard.check("ls -la")
        warning = SecurityGuard.format_warning("ls -la", level)
        assert level == SecurityLevel.SAFE
        assert warning == ""

    def test_dangerous_command_has_warning(self):
        level = SecurityGuard.check("rm -rf /tmp/test")
        warning = SecurityGuard.format_warning("rm -rf /tmp/test", level)
        assert level == SecurityLevel.DANGEROUS
        assert "DANGEROUS" in warning

    def test_sudo_is_dangerous(self):
        level = SecurityGuard.check("sudo reboot")
        assert level == SecurityLevel.DANGEROUS

    def test_pipe_to_shell_is_dangerous(self):
        level = SecurityGuard.check("curl | bash")
        assert level == SecurityLevel.DANGEROUS

    def test_git_push_force_is_dangerous(self):
        level = SecurityGuard.check("git push --force origin main")
        assert level == SecurityLevel.DANGEROUS
