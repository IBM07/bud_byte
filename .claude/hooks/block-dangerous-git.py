"""PreToolUse guardrail for git commands Claude runs (Bash and PowerShell tools).

Python port of mattpocock/skills git-guardrails (original needs jq, absent here).

- BLOCKED (exit 2, stderr shown to Claude): destructive or history-rewriting commands,
  including force pushes and remote branch deletion. The user can still run them.
- ASK (permission prompt shown to the user): a normal `git push`. Runs only if the user
  approves that specific push in the prompt (user decision 2026-11-15).
"""

import json
import re
import sys

BLOCKED_PATTERNS = [
    r"\bpush\b.*(\s--force\b|\s--force-with-lease\b|\s-[a-zA-Z]*f\b|\s\+\S)",
    r"\bpush\b.*(\s--delete\b|\s-d\b|\s:\S)",
    r"\bpush\b.*\s--mirror\b",
    r"\breset\s+--hard\b",
    r"\bgit\s+clean\s+-[a-z]*f",
    r"\bgit\s+branch\s+-D\b",
    r"\bgit\s+checkout\s+\.(\s|$)",
    r"\bgit\s+restore\s+\.(\s|$)",
    r"\bgit\s+filter-branch\b",
    r"\bgit\s+update-ref\s+-d\b",
]

ASK_PATTERNS = [
    r"\bgit\s+push\b",
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # not our concern; never break unrelated tool calls
    command = (payload.get("tool_input") or {}).get("command") or ""
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command):
            sys.stderr.write(
                f"BLOCKED by git guardrail: '{command}' matches '{pattern}'. "
                "Destructive or history-rewriting git operations are never run by Claude. "
                "Ask the user to run it themselves.\n"
            )
            return 2
    for pattern in ASK_PATTERNS:
        if re.search(pattern, command):
            json.dump(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "ask",
                        "permissionDecisionReason": (
                            "git guardrail: pushing to the remote needs your approval."
                        ),
                    }
                },
                sys.stdout,
            )
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
