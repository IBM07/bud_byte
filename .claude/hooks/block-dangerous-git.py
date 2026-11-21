"""PreToolUse guardrail for git commands Claude runs (Bash and PowerShell tools).

Started as a Python port of mattpocock/skills git-guardrails (original needs jq, absent here).

- BLOCKED (exit 2, stderr shown to Claude): destructive or history-rewriting commands,
  including force pushes and remote branch deletion. The user can still run them.
- ASK (permission prompt shown to the user): a normal `git push`. Runs only if the user
  approves that specific push in the prompt (user decision 2026-11-15).

The command is parsed into shell words (quotes, separators, line continuations), not
pattern-matched, so quoting cannot hide a flag or a separator. If it cannot be parsed and
mentions git, the hook asks rather than guessing.
"""

from __future__ import annotations

import json
import re
import shlex
import sys

BLOCK, ASK, ALLOW = "block", "ask", "allow"
_RANK = {ALLOW: 0, ASK: 1, BLOCK: 2}

# Global options that take a value: `-C dir`, `-Cdir`, `--git-dir=x`, `--git-dir x`.
_SHORT_WITH_VALUE = ("-C", "-c")
_LONG_WITH_VALUE = ("--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env")
_SEPARATORS = {";", "&", "&&", "|", "||", "\n", "(", ")", "|&", ";;"}
_SHELLS = {"bash", "sh", "zsh", "pwsh", "powershell", "cmd"}
# Heredoc: keep the rest of the header line (`cat <<EOF && git push -f`), drop the body.
_HEREDOC = re.compile(r"<<-?\s*([\"']?)(\w+)\1([^\n]*)\n.*?\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
# `$(...)` runs even inside double quotes and unquoted heredocs; innermost first.
_SUBSTITUTION = re.compile(r"\$\(([^()]*)\)")
# Pathspecs that mean "everything here", not one named file.
_WHOLE_TREE = {".", "./", ":/", ":/.", ":(top)", "*"}


def _short_bundle(arg: str) -> str:
    """Letters of a short-option bundle (`-fv` -> "fv"); "" for anything else."""
    return arg[1:] if arg.startswith("-") and not arg.startswith("--") and len(arg) > 1 else ""


def _is_long(arg: str, long: str) -> bool:
    """`--force`, `--force=x`, or a unique-enough prefix git also accepts (`--for`)."""
    name = arg.split("=", 1)[0]
    return name == long or (name.startswith("--") and len(name) >= 5 and long.startswith(name))


def _has(args: list[str], long: str, short: str = "") -> bool:
    return any(_is_long(a, long) or (short and short in _short_bundle(a)) for a in args)


def _whole_tree(args: list[str]) -> bool:
    return any(a in _WHOLE_TREE for a in args)


def _classify_git(sub: str, args: list[str]) -> str:
    if sub == "push":
        if _has(args, "--force", "f") or _has(args, "--force-with-lease"):
            return BLOCK
        if _has(args, "--delete", "d") or _has(args, "--mirror"):
            return BLOCK
        if any(a.startswith(("+", ":")) and len(a) > 1 for a in args):
            return BLOCK  # +refspec forces, :refspec deletes
        return ASK
    if sub == "reset" and _has(args, "--hard"):
        return BLOCK
    if sub == "clean" and _has(args, "--force", "f"):
        return BLOCK
    if sub == "branch":
        deleting = _has(args, "--delete", "d")
        if any("D" in _short_bundle(a) for a in args) or (deleting and _has(args, "--force", "f")):
            return BLOCK
    if sub == "checkout" and _whole_tree(args):
        return BLOCK  # discard every unstaged change
    if sub == "restore" and _whole_tree(args):
        # Exact flags only: in `-sSTABLE` the S is part of the --source value, not --staged.
        staged = any(_is_long(a, "--staged") or a == "-S" for a in args)
        worktree = any(_is_long(a, "--worktree") or a == "-W" for a in args)
        if not staged or worktree:  # `restore --staged .` only unstages, nothing is lost
            return BLOCK
    if sub == "filter-branch" or (sub == "update-ref" and "-d" in args):
        return BLOCK
    return ALLOW


def _is_git(word: str) -> bool:
    name = re.split(r"[\\/]", word)[-1].lower()
    return name in ("git", "git.exe")


def _classify_words(words: list[str]) -> str:
    """Classify one simple command (no separators)."""
    for i, word in enumerate(words):
        if _is_git(word):
            j = i + 1
            while j < len(words) and words[j].startswith("-"):
                opt = words[j]
                takes_value = opt in _SHORT_WITH_VALUE or opt in _LONG_WITH_VALUE
                j += 2 if takes_value else 1  # `-Cdir` / `--git-dir=x` carry their value
            if j < len(words):
                return _classify_git(words[j], words[j + 1 :])
            return ALLOW
        name = re.split(r"[\\/]", word)[-1].lower().removesuffix(".exe")
        if name in _SHELLS:
            # `bash -c "git push -f"`: the script is one word; classify it as a command.
            return max((classify(w) for w in words[i + 1 :]), key=_RANK.__getitem__, default=ALLOW)
    return ALLOW


def classify(command: str) -> str:
    # Line continuations. Bash removes backslash-newline outright, even mid-word
    # (`git re\<nl>set` runs `git reset`); PowerShell's backtick-newline joins tokens.
    command = command.replace("\\\r\n", "").replace("\\\n", "")
    command = command.replace("`\r\n", " ").replace("`\n", " ")
    # Substitutions execute wherever they sit (double quotes, unquoted heredocs), so classify
    # each one as a command of its own. Single-quoted literals get the same treatment: a false
    # block on quoted text is the safe direction.
    verdict = ALLOW
    for inner in _SUBSTITUTION.findall(command):
        verdict = max(verdict, classify(inner), key=_RANK.__getitem__)
    command = _HEREDOC.sub(r"\3", command)  # heredoc bodies are data; the header line is not
    # Unquoted newlines separate commands like `;` does, so they are punctuation, not whitespace.
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:  # unbalanced quotes etc.
        fallback = ASK if re.search(r"git", command, re.I) else ALLOW
        return max(verdict, fallback, key=_RANK.__getitem__)
    segment: list[str] = []
    for tok in [*tokens, ";"]:
        if tok in _SEPARATORS or (tok and set(tok) <= set(";&|()\n")):
            result = _classify_words(segment)
            if _RANK[result] > _RANK[verdict]:
                verdict = result
            segment = []
        else:
            segment.append(tok)
    return verdict


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # not our concern; never break unrelated tool calls
    command = str((payload.get("tool_input") or {}).get("command") or "")
    verdict = classify(command)
    if verdict == BLOCK:
        sys.stderr.write(
            f"BLOCKED by git guardrail: '{command}'. "
            "Destructive or history-rewriting git operations are never run by Claude. "
            "Ask the user to run it themselves.\n"
        )
        return 2
    if verdict == ASK:
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


if __name__ == "__main__":
    sys.exit(main())
