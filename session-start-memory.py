#!/usr/bin/env python3
"""
Session Wizard — SessionStart Hook
===================================
Reads last-session.md from the project's memory directory,
injects it into the conversation context via hookSpecificOutput,
then deletes the file (one-shot consumption).

Install:
  1. Copy to ~/.claude/hooks/session-start-memory.py
  2. Add to ~/.claude/settings.json:
     {
       "hooks": {
         "sessionStart": [{
           "type": "command",
           "command": "python ~/.claude/hooks/session-start-memory.py"
         }]
       }
     }
"""

import json
import os
import pathlib
import re
import sys


def sanitize_cwd(cwd: str) -> str:
    """Sanitize a working directory path the same way Claude Code does.

    Replaces path separators and colons with dashes, strips leading dashes.

    Examples:
        /home/user/projects/my-app  →  home-user-projects-my-app
        D:\\projects\\my-app         →  D-projects-my-app
        C:\\Users\\PC\\dev\\app      →  C-Users-PC-dev-app
    """
    sanitized = cwd.replace("\\", "-").replace("/", "-").replace(":", "-")
    sanitized = re.sub(r"^-+", "", sanitized)
    return sanitized


def main():
    cwd = os.getcwd()
    sanitized = sanitize_cwd(cwd)
    memory_dir = pathlib.Path.home() / ".claude" / "projects" / sanitized / "memory"
    handoff_file = memory_dir / "last-session.md"

    if not handoff_file.exists():
        # No handoff — exit silently
        print(json.dumps({}))
        return

    try:
        content = handoff_file.read_text(encoding="utf-8")
        handoff_file.unlink()

        output = {
            "hookSpecificOutput": {
                "additionalContext": (
                    "[session-memory] Previous session summary "
                    "picked up and injected:\n\n"
                    f"{content}\n"
                    "[/session-memory]"
                )
            }
        }
        print(json.dumps(output))

    except Exception as e:
        print(json.dumps({}), file=sys.stdout)
        print(f"session-wizard hook error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
