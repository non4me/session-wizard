# 🧙 Session Wizard

**Full session lifecycle management for Claude Code** — analyzes sessions on close, routes knowledge to memory and skills, and passes context to the next session automatically.

> Auto-dream cleans your memory. Session Wizard makes sure nothing worth remembering gets lost in the first place.

## The Problem

Claude Code's **Auto-memory** takes notes. **Auto-dream** cleans them up. But neither does three things:

1. **Route knowledge** — decide what goes into memory vs. what becomes a reusable skill
2. **Hand off context** — give the next session a structured summary so it can pick up where you left off
3. **Evolve skills** — detect reusable patterns and update skills automatically

After 20+ sessions, Claude either forgets critical decisions or drowns in noise. Session Wizard solves this.

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌───────────────────────────────────────┐
│  Session N   │────▶│     /es       │────▶│ ~/.claude/projects/{cwd}/memory/     │
│  (working)   │     │  (analysis)  │     │   ├── MEMORY.md (index)              │
│              │     │              │     │   ├── last-session.md (handoff)      │
└─────────────┘     └──────────────┘     │   └── *.md (topic files)             │
                                          │ ~/.claude/skills/ (if skill updated) │
                                          └──────────────────┬──────────────────┘
                                                             │
                    ┌──────────────┐                         │
                    │ Session N+1  │◀────────────────────────┘
                    │ sessionStart │  Python hook reads
                    │  hook fires  │  last-session.md → JSON
                    │              │  → additionalContext
                    └──────────────┘  → deletes file
```

**`/es`** analyzes the session and writes:
- Classified memory files (user prefs, project state, bugs, references)
- Skill updates (if a reusable pattern was discovered)
- `last-session.md` — structured handoff for the next session

**SessionStart hook** fires on the next session:
- Reads `last-session.md`
- Injects it as `[session-memory]` into the conversation
- Deletes the file (one-shot consumption — no stale context)

## What `/es` Does (6 Steps)

| Step | Action |
|------|--------|
| 1. **Analyze** | Scans full conversation, classifies findings into `user` / `feedback` / `project` / `reference` / `pitfall` types |
| 2. **Save to Memory** | Creates/updates memory files with YAML frontmatter, updates `MEMORY.md` index |
| 3. **Update Active Work** | Maintains `## Active Work` and `## Completed` sections with exact next steps |
| 4. **Update Skills** | If a reusable pattern was found → updates global or project skill |
| 5. **Write Handoff** | Saves `last-session.md` with date, branch, completed items, next steps, key decisions |
| 6. **Respond** | Compact summary: what was done, what's next, memory stats |

## Installation

### 1. Install the skill

**Global (all projects):**
```bash
git clone https://github.com/non4me/session-wizard.git
cp -r session-wizard ~/.claude/skills/session-wizard
```

**Or with npx:**
```bash
npx skills add non4me/session-wizard
```

### 2. Install the SessionStart hook

Copy the hook script:
```bash
mkdir -p ~/.claude/hooks
cp session-wizard/scripts/session-start-memory.py ~/.claude/hooks/
```

Register it in `~/.claude/settings.json`:
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

> **Windows**: use `python` or `python3` depending on your setup. The script handles both Windows and Unix paths.

### 3. Verify

```bash
# Start a Claude Code session
# Do some work
# Type /es
# Check that memory/last-session.md was created
# Start a new session
# You should see [session-memory] at the start
```

## Session Wizard vs Auto-dream

| Feature | Auto-dream | Session Wizard |
|---------|-----------|----------------|
| Cleans memory files | ✅ | ❌ (not its job) |
| Routes knowledge to memory | ❌ (auto-memory does raw capture) | ✅ (classified by type) |
| Routes knowledge to skills | ❌ | ✅ |
| Session-to-session handoff | ❌ | ✅ |
| Tracks active work & next steps | ❌ | ✅ |
| Runs automatically | ✅ (background) | `/es` on demand |
| Logs pitfalls & solutions | ❌ | ✅ (`problems-and-fixes.md`) |

**They complement each other.** Auto-dream keeps memory clean. Session Wizard makes sure the right knowledge gets to the right place and the next session starts warm.

## Memory Directory Structure

```
~/.claude/projects/{sanitized_cwd}/memory/
├── MEMORY.md                 ← index of all memory files
├── last-session.md           ← handoff file (auto-deleted by hook)
├── problems-and-fixes.md     ← accumulated pitfalls & solutions
└── *.md                      ← topic memory files with YAML frontmatter
```

## Compatibility

- **Claude Code**: Full support (skills + hooks)
- **OS**: Windows, macOS, Linux
- **Works with Auto-dream**: Yes
- **Works with Auto-memory**: Yes
- **Python**: 3.8+ (no external dependencies)

## License

MIT — see [LICENSE](LICENSE)

## Author

[@non4me](https://github.com/non4me)
