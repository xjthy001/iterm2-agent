"""Tests for the security module."""

from iterm2_agent.security import SecurityGuard, SecurityLevel


class TestSecurityGuard:
    def test_safe_commands(self):
        safe_commands = [
            "ls -la",
            "pwd",
            "echo hello",
            "cat README.md",
            "git status",
            "python3 --version",
        ]
        for cmd in safe_commands:
            result = SecurityGuard.check(cmd)
            assert result == SecurityLevel.SAFE, f"{cmd!r} should be SAFE, got {result}"

    def test_caution_commands(self):
        caution_commands = [
            "cd /tmp",
            "mkdir new_dir",
            "npm install express",
            "git commit -m 'test'",
            "docker ps",
            "make build",
        ]
        for cmd in caution_commands:
            result = SecurityGuard.check(cmd)
            assert result == SecurityLevel.CAUTION, f"{cmd!r} should be CAUTION, got {result}"

    def test_dangerous_commands(self):
        dangerous_commands = [
            "rm -rf /",
            "sudo apt install",
            "chmod 777 file",
            "kill -9 1234",
            "dd if=/dev/zero of=/dev/sda",
        ]
        for cmd in dangerous_commands:
            result = SecurityGuard.check(cmd)
            assert result == SecurityLevel.DANGEROUS, f"{cmd!r} should be DANGEROUS, got {result}"

    def test_unknown_defaults_to_caution(self):
        result = SecurityGuard.check("some-unknown-tool --flag")
        assert result == SecurityLevel.CAUTION

    def test_case_insensitive(self):
        assert SecurityGuard.check("LS -la") == SecurityLevel.SAFE
        assert SecurityGuard.check("RM -rf /tmp") == SecurityLevel.DANGEROUS

    def test_whitespace_handling(self):
        assert SecurityGuard.check("  ls -la  ") == SecurityLevel.SAFE
        assert SecurityGuard.check("  rm -rf /  ") == SecurityLevel.DANGEROUS

    def test_format_warning_safe(self):
        warning = SecurityGuard.format_warning("ls", SecurityLevel.SAFE)
        assert warning == ""

    def test_format_warning_caution(self):
        warning = SecurityGuard.format_warning("npm install", SecurityLevel.CAUTION)
        assert "CAUTION" in warning
        assert "npm install" in warning

    def test_format_warning_dangerous(self):
        warning = SecurityGuard.format_warning("rm -rf /", SecurityLevel.DANGEROUS)
        assert "DANGEROUS" in warning
        assert "rm -rf /" in warning
