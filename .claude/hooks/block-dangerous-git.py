"""PreToolUse guardrail: block destructive git commands before Claude runs them.

Python port of mattpocock/skills git-guardrails (original needs jq, absent here).
Covers both the Bash and PowerShell tools. Exit code 2 = block, stderr shown to Claude.
The user can still run these commands themselves.
"""
import json
import re
import sys

DANGEROUS_PATTERNS = [
    r"\bgit\s+push\b",
    r"\bpush\s+--force\b",
    r"\breset\s+--hard\b",
    r"\bgit\s+clean\s+-[a-z]*f",
    r"\bgit\s+branch\s+-D\b",
    r"\bgit\s+checkout\s+\.(\s|$)",
    r"\bgit\s+restore\s+\.(\s|$)",
    r"\bgit\s+filter-branch\b",
    r"\bgit\s+update-ref\s+-d\b",
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # not our concern; never break unrelated tool calls
    command = (payload.get("tool_input") or {}).get("command") or ""
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            sys.stderr.write(
                f"BLOCKED by git guardrail: '{command}' matches '{pattern}'. "
                "The user has not authorised destructive or remote git operations. "
                "Ask the user to run it themselves or to explicitly approve it.\n"
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
