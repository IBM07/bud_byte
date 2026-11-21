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

# An option value, possibly quoted: -C "C:/Users/Some One/repo" is one value.
_VAL = r"(?:\"[^\"]*\"|'[^']*'|\S+)"
# `git` / `git.exe` plus any global options before the subcommand, e.g. `git -C . push`,
# `git -c k=v clean`, `git --git-dir=.git push`. Options that take a separate value
# (-C, -c, --git-dir ...) consume it; other flags (--no-pager, -P ...) stand alone.
_GIT = (
    r"\bgit(?:\.exe)?[\"']?"  # closing quote of a quoted full path: "C:/.../git.exe" push
    rf"(?:\s+(?:-[Cc]|--(?:git-dir|work-tree|namespace|exec-path|config-env))(?:=|\s+){_VAL}"
    rf"|\s+--?[A-Za-z][\w-]*(?:={_VAL})?)*"
    r"\s+"
)
# The rest of this command only: stop at ; & | or a newline, so flags of a chained
# command (`git push origin x && ls -ld .`) are not read as git flags.
_SEG = r"[^;&|\n]*"
# A quote may wrap a refspec: git push origin "+HEAD:main" is still a force push.
_Q = r"[\"']?"

BLOCKED_PATTERNS = [
    # Force: long options, -f anywhere in a bundle (-f, -fv, -vf), or a +refspec.
    rf"{_GIT}push\b{_SEG}(\s--force\b|\s-[a-zA-Z]*f[a-zA-Z]*\b|\s{_Q}\+\S)",
    # Delete: --delete, -d anywhere in a bundle, or a :refspec.
    rf"{_GIT}push\b{_SEG}(\s--delete\b|\s-[a-zA-Z]*d[a-zA-Z]*\b|\s{_Q}:\S)",
    rf"{_GIT}push\b{_SEG}\s--mirror\b",
    rf"{_GIT}reset\b{_SEG}\s--hard\b",
    rf"{_GIT}clean\b{_SEG}\s(-[a-zA-Z]*f|--force\b)",
    # Force-delete a branch: -D (in any bundle), or delete + force in any spelling/order.
    rf"{_GIT}branch\b{_SEG}\s-[a-zA-Z]*D",
    rf"{_GIT}branch\b{_SEG}\s-[a-zA-Z]*(d[a-zA-Z]*f|f[a-zA-Z]*d)",
    rf"{_GIT}branch\b{_SEG}\s(--delete\b|-[a-zA-Z]*d){_SEG}\s(--force\b|-[a-zA-Z]*f)",
    rf"{_GIT}branch\b{_SEG}\s(--force\b|-[a-zA-Z]*f){_SEG}\s(--delete\b|-[a-zA-Z]*d)",
    rf"{_GIT}checkout\s+\.(\s|$)",
    rf"{_GIT}restore\s+\.(\s|$)",
    rf"{_GIT}filter-branch\b",
    rf"{_GIT}update-ref\s+-d\b",
]

ASK_PATTERNS = [
    rf"{_GIT}push\b",
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
