# Session Wizard — Setup Guide

## Overview

Session Wizard has two components:
1. **`/es` command** — the SKILL.md that analyzes sessions and writes memory + handoff
2. **`session-start-memory.py`** — a SessionStart hook that injects the handoff into the next session

The hook uses Claude Code's `hookSpecificOutput.additionalContext` mechanism to inject
the previous session's context, then deletes the handoff file to prevent stale injection.

---

## Installing the Skill

### Global install (recommended — works across all projects)

```bash
cp -r session-wizard/ ~/.claude/skills/session-wizard/
```

### Project install (single project only)

```bash
cp -r session-wizard/ .claude/skills/session-wizard/
```

---

## The SessionStart Hook

### How it works

Claude Code fires `sessionStart` hooks at the beginning of every new session.
The hook script:

1. Gets the current working directory
2. Sanitizes it the same way Claude Code does (e.g., `D:\projects\my-app` → `D--projects-my-app`)
3. Looks for `~/.claude/projects/{sanitized_cwd}/memory/last-session.md`
4. If found: reads it, deletes it, returns JSON that Claude Code injects into the conversation
5. If not found: exits silently

### The Python script

Save as `~/.claude/hooks/session-start-memory.py`:

```python
#!/usr/bin/env python3
"""SessionStart hook for session-wizard.
Reads last-session.md from the project's memory directory,
injects it into the conversation context, then deletes the file.
"""

import json
import os
import pathlib
import re
import sys


def sanitize_cwd(cwd: str) -> str:
    """Sanitize a working directory path the same way Claude Code does.
    Replaces path separators and colons with dashes.
    """
    sanitized = cwd.replace("\\", "-").replace("/", "-").replace(":", "-")
    # Remove leading dash if present (from drive letter colon)
    sanitized = re.sub(r"^-+", "", sanitized)
    return sanitized


def main():
    cwd = os.getcwd()
    sanitized = sanitize_cwd(cwd)
    memory_dir = pathlib.Path.home() / ".claude" / "projects" / sanitized / "memory"
    handoff_file = memory_dir / "last-session.md"

    if not handoff_file.exists():
        # No handoff file — exit silently, no context to inject
        print(json.dumps({}))
        return

    try:
        content = handoff_file.read_text(encoding="utf-8")
        # Delete after reading — one-shot consumption
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
        # Don't break the session if something goes wrong
        print(json.dumps({}), file=sys.stdout)
        print(f"session-wizard hook error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
```

### Registering the hook

Add to your **global** settings at `~/.claude/settings.json`:

```json
{
  "hooks": {
    "sessionStart": [
      {
        "type": "command",
        "command": "python ~/.claude/hooks/session-start-memory.py"
      }
    ]
  }
}
```

Or **project-level** at `.claude/settings.json` if you only want it for specific projects.

**Windows note**: Use `python` or `python3` depending on your setup. The script is
cross-platform — it handles both Windows and Unix path separators.

---

## Verifying the Setup

### Quick test

```bash
# 1. Run the hook manually from your project directory
cd /path/to/your/project
python ~/.claude/hooks/session-start-memory.py

# If last-session.md exists: prints JSON with additionalContext, deletes the file
# If not: prints {}
```

### Full integration test

1. Start a Claude Code session in your project
2. Do some work
3. Type `/es`
4. Verify `last-session.md` was created in the memory directory
5. Close the session
6. Start a new session
7. You should see `[session-memory] Previous session summary picked up and injected:` at the start
8. Verify `last-session.md` was deleted

---

## Path Sanitization Reference

The sanitization must match Claude Code's internal logic. Examples:

| Working directory | Sanitized |
|---|---|
| `/home/user/projects/my-app` | `home-user-projects-my-app` |
| `D:\projects\my-app` | `D-projects-my-app` |
| `C:\Users\PC\dev\any-project` | `C-Users-PC-dev-any-project` |

If the hook can't find `last-session.md`, the most likely cause is a sanitization mismatch.
Check `~/.claude/projects/` to see how Claude Code names your project directories
and adjust the `sanitize_cwd` function if needed.

---

## Compatibility

| Feature | Status |
|---|---|
| Claude Code | Full support |
| Windows / macOS / Linux | Cross-platform (Python) |
| Works with Auto-dream | Yes — Auto-dream cleans memory, session-wizard routes + hands off |
| Works with Auto-memory | Yes — Auto-memory captures raw notes, session-wizard classifies them |
| Multiple projects | Yes — each project gets its own memory directory |
