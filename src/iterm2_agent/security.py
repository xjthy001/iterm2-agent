"""Command security classification."""

from __future__ import annotations

from enum import Enum


class SecurityLevel(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"


# Commands considered safe — read-only or informational
SAFE_PREFIXES = frozenset({
    "ls", "pwd", "echo", "cat", "head", "tail", "wc", "date", "whoami",
    "which", "where", "file", "stat", "df", "du", "uname", "hostname",
    "env", "printenv", "id", "groups", "uptime", "ps", "top", "htop",
    "git status", "git log", "git diff", "git branch", "git remote",
    "python --version", "python3 --version", "node --version",
    "npm --version", "pip --version", "pip3 --version",
    "cargo --version", "go version", "java --version",
})

# Commands that modify the system — require caution
CAUTION_PREFIXES = frozenset({
    "cd", "mkdir", "touch", "cp", "mv", "git add", "git commit",
    "git checkout", "git switch", "git merge", "git rebase",
    "git push", "git pull", "git fetch", "git stash",
    "npm install", "npm run", "pip install", "pip3 install",
    "cargo build", "cargo run", "go build", "go run",
    "make", "cmake", "docker", "docker-compose",
    "brew install", "brew update", "brew upgrade",
})

# Commands that are destructive or require elevated privileges
DANGEROUS_PREFIXES = frozenset({
    "rm", "sudo", "chmod", "chown", "chgrp",
    "kill", "killall", "pkill",
    "dd", "mkfs", "fdisk", "mount", "umount",
    "iptables", "systemctl", "launchctl",
    "curl | sh", "curl | bash", "wget | sh", "wget | bash",
    "git push --force", "git reset --hard", "git clean -f",
    "> /dev/", ">> /dev/",
})


class SecurityGuard:
    """Classify commands by security risk level."""

    @classmethod
    def check(cls, command: str) -> SecurityLevel:
        """Return the security level for a command."""
        stripped = command.strip()
        lower = stripped.lower()

        for prefix in DANGEROUS_PREFIXES:
            if lower.startswith(prefix):
                return SecurityLevel.DANGEROUS

        for prefix in SAFE_PREFIXES:
            if lower.startswith(prefix):
                return SecurityLevel.SAFE

        for prefix in CAUTION_PREFIXES:
            if lower.startswith(prefix):
                return SecurityLevel.CAUTION

        # Unknown commands default to caution
        return SecurityLevel.CAUTION

    @classmethod
    def format_warning(cls, command: str, level: SecurityLevel) -> str:
        """Generate a warning string for non-safe commands."""
        if level == SecurityLevel.SAFE:
            return ""
        if level == SecurityLevel.DANGEROUS:
            return (
                f"⚠️ DANGEROUS COMMAND: `{command}`\n"
                "This command may cause irreversible changes. "
                "Proceed with extreme caution."
            )
        return (
            f"⚡ CAUTION: `{command}`\n"
            "This command modifies the system. Verify intent before proceeding."
        )
