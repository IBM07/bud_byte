"""Tests for the Claude Code PreToolUse git guardrail (.claude/hooks/block-dangerous-git.py).

Lives here because this is the repo's only pytest root; the hook itself is plain stdlib Python.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "block-dangerous-git.py"


def _decide(command: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    # Fixed argv (this interpreter + a repo file); the command under test is only stdin data.
    proc = subprocess.run(  # noqa: S603
        [sys.executable, str(HOOK)], input=payload, capture_output=True, text=True, check=False
    )
    if proc.returncode == 2:
        return "block"
    if proc.stdout.strip():
        return json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"]
    return "allow"


@pytest.mark.parametrize(
    "command",
    [
        "git push --force origin main",
        "git push -f origin main",
        "git push -fv origin main",  # bundled short options
        "git push -vf origin main",
        'git push origin "+HEAD:main"',  # quoted force refspec
        "git push origin '+main'",
        "git push --delete origin feat/x",
        "git push -dv origin feat/x",
        'git push origin ":feat/x"',  # quoted delete refspec
        "git -C . push --force origin main",
        'git -C "C:/Users/Some One/repo" push -f origin main',
        "git.exe push --force origin main",
        '"C:/Program Files/Git/bin/git.exe" push --force origin main',  # quoted full path
        "git reset --hard HEAD~1",
        "git -C . reset --hard",
        "git reset -q --hard HEAD~1",
        "git -c core.x=1 clean -fd",
        "git clean --force -d",
        "git clean -x -f",
        "git.exe clean -fdx",
        "git --git-dir=.git branch -D old",
        "git branch -Dq old",
        "git branch --delete --force old",
        "git branch -d -f old",
        "git branch -df old",
    ],
)
def test_destructive_git_is_blocked(command: str) -> None:
    assert _decide(command) == "block"


@pytest.mark.parametrize(
    "command",
    [
        "git push origin main",
        "git push -u origin feat/x",
        "git -C . push origin main",  # global options before the subcommand
        "git -C /c/cabal push origin main",
        "git -c push.default=current push",
        "git --git-dir=.git push origin main",
        "git --git-dir .git push origin main",
        "cd /c/cabal && git -C . push",
        'git -C "C:/Users/Some One/repo" push origin main',  # quoted path with a space
        "git -C 'C:/Users/Some One/repo' push origin main",
        "git.exe push origin main",  # PowerShell / Windows spelling
        "& 'C:/Program Files/Git/cmd/git.exe' push origin main",  # PowerShell call operator
        "git push -u origin feat/x && ls -ld .",  # flags of a later command are not push flags
    ],
)
def test_normal_push_asks_the_user(command: str) -> None:
    assert _decide(command) == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git log --oneline -5",
        "git commit -m 'push fix'",
        "git fetch origin",
        'git commit -m "push docs" && rm -rf build',
        "git branch -d merged-branch",  # safe delete (refuses unmerged work)
        "git clean -n",  # dry run
    ],
)
def test_safe_git_is_allowed(command: str) -> None:
    assert _decide(command) == "allow"
