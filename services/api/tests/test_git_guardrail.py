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
        # Shell quoting must not hide the destructive part (review round 2).
        "git clean -e 'cache;old' -fd",  # quoted separator inside an argument
        "git push origin 'a|b' --force",
        "git push '--force' origin main",  # quoted flag
        "git reset '--hard'",
        "git -C/cabal push --force",  # attached option value
        "git push \\\n  --force origin main",  # backslash line continuation
        "git checkout -- .",
        "git restore --worktree .",
        "git restore --staged --worktree -- .",
        'bash -c "git push -f origin main"',  # nested shell string
        "git status; git push -f",
        "git status\ngit push -f",
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
        'git -c core.sshCommand="ssh -i /tmp/id" push origin main',  # partially quoted value
        "git -C/cabal push origin main",  # attached option value
        "git --no-pager -C . push",
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
        "git checkout -- src/app.py",  # restoring one named file is not a wholesale discard
        "git restore --staged src/app.py",
        "echo 'git push --force is blocked'",  # text, not a git invocation
        # A heredoc body is data: words like "git push --force" in a commit message are not run.
        "git commit -F - <<'EOF'\nfix: guard git push --force\n\ngit reset --hard is blocked\nEOF",
    ],
)
def test_safe_git_is_allowed(command: str) -> None:
    assert _decide(command) == "allow"
