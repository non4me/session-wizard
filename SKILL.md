---
name: session-wizard
description: >
  Full session lifecycle management — analyzes the current session on close, routes knowledge to memory and skills,
  and passes context to the next session via a handoff file + SessionStart hook.
  Use this skill whenever the user types /es, "end session", "wrap up", "save session", "session summary",
  or any variation of closing/ending a work session. Also use when the user asks to save progress,
  create a session handoff, or prepare context for the next session. This skill should trigger even for
  short sessions — every session produces at least a state update and a handoff file.
---

# Session Wizard

A session lifecycle skill that solves three problems Auto-dream and Auto-memory don't:

1. **Knowledge routing** — classifies session insights and routes them to memory files OR skill files, not just memory
2. **Session handoff** — writes a structured summary that the next session reads on startup, so Claude never starts cold
3. **Skill evolution** — detects reusable patterns and updates skills, creating a feedback loop from real work

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

## Where Things Live

Session Wizard follows Claude Code's native project memory layout:

```
~/.claude/projects/{sanitized_cwd}/memory/
├── MEMORY.md                 ← index of all memory files
├── last-session.md           ← handoff file (auto-deleted by hook)
├── problems-and-fixes.md     ← accumulated pitfalls
└── *.md                      ← topic memory files
```

The `{sanitized_cwd}` is Claude Code's standard path sanitization of your project's working directory
(e.g., `D--projects-any-project` for `D:\projects\any-project`).

Skills directories:
- **Global skills**: `~/.claude/skills/` (cross-project, reusable everywhere)
- **Project skills**: `./.claude/skills/` (specific to current project)

Override memory location via a config file if your setup differs:

```markdown
<!-- .claude/session-wizard.config.md -->
memory_dir: ~/.claude/projects/{sanitized_cwd}/memory
skills_global_dir: ~/.claude/skills
skills_project_dir: ./.claude/skills
```

---

## The /es Command

When the user invokes `/es`, perform ALL steps below before responding. This is a blocking requirement — do not skip steps, do not ask clarifying questions.

### Step 1: Analyze the Session

Review the entire conversation. Classify every notable piece of information into one of these types:

| Type | What to look for | Examples |
|------|-----------------|----------|
| `user` | Facts about the user: role, preferences, expertise, workflow habits | "I prefer Tailwind over Bootstrap", "I work in Angular 18" |
| `feedback` | Corrections or confirmations of Claude's approach | "Don't use classes, use functions", "This approach works well" |
| `project` | State changes: new features, architecture decisions, blockers, completions | "Switched from REST to GraphQL", "Auth module is done" |
| `reference` | External resources discovered or used | URLs, API docs, libraries, services, tools |
| `pitfall` | Problems encountered and their solutions | Build errors, tricky bugs, non-obvious gotchas |

Be thorough. Scan the full conversation — important context often hides in early messages or casual remarks.

### Step 2: Save to Memory

For each item identified in Step 1:

1. **Check for existing memory files first** — update rather than duplicate. Read the memory index to see what already exists.
2. **Write or update memory files** using this frontmatter format:

```yaml
---
name: descriptive-kebab-case-name
description: One-line summary of what this memory contains
type: user | feedback | project | reference
---

[Content in markdown]
```

3. **Update the memory index** (`MEMORY.md`) if new files were created. Keep index entries to one line each:
   ```markdown
   - [Name](filename.md) — one-line description
   ```

4. **Add pitfalls** to `problems-and-fixes.md` (create if it doesn't exist). Format:
   ```markdown
   ## [Short problem title]
   **Problem**: What went wrong
   **Cause**: Why it happened
   **Fix**: How it was resolved
   **Date**: YYYY-MM-DD
   ```

### Step 3: Update Active Work

In `MEMORY.md`, maintain two sections:

**`## Active Work`** — update with:
- What was being worked on this session
- Current status: `in progress` / `blocked` / `complete`
- The exact next step — specific enough that the next session can continue without re-discovery
- Git branch name if relevant

**`## Completed`** — move items here when work is finished this session.

### Step 4: Update Skills (if applicable)

If during the session a **reusable** technique, pattern, or tool was discovered:

1. Evaluate scope:
   - **Cross-project** (useful everywhere) → global skills directory
   - **Project-specific** (useful only here) → project skills directory

2. Only create or update a skill if the pattern is genuinely reusable — not a one-off fix. Good candidates:
   - A workflow that was refined through trial and error
   - A technique that solved a recurring class of problems
   - A configuration pattern that's non-obvious but reliable
   - A testing/debugging approach that proved effective

3. If updating an existing skill, preserve its structure and add the new knowledge. Don't rewrite what already works.

### Step 5: Write Session Handoff

Save to the project's memory directory as `last-session.md`
(typically `~/.claude/projects/{sanitized_cwd}/memory/last-session.md`):

```markdown
---
date: YYYY-MM-DD
branch: <current git branch or "N/A">
---

## Completed
- [bullet list of what was accomplished this session]

## Next
[exact continuation point — be specific enough to resume without context]

## Key Decisions
[any non-obvious decisions made and their reasoning, if applicable]
```

This file is the bridge between sessions. The SessionStart hook will:
1. Read it and inject contents as `[session-memory]` into the conversation
2. Delete it immediately after reading to prevent stale context

**Always write this file**, even if the session was trivial. The hook depends on it.

### Step 6: Respond

Output a compact summary — no fluff:

```
Session saved.
Completed: [bullet list]
Next: [continuation point]
Memory: [N new / M updated files]
Type /exit to close.
```

---

## Rules

- **Never ask clarifying questions** — analyze and save silently
- **Never skip steps** even if the session was short
- **Always write `last-session.md`** — the SessionStart hook depends on it
- **Update before create** — check for existing memory files before writing new ones
- **If nothing notable happened**, still update Active Work state and write the handoff
- **Always end with** "Type /exit to close."

---

## SessionStart Hook

The hook is a Python script that fires at the start of every session. It:
1. Computes the memory path from `cwd` using Claude Code's path sanitization
2. Reads `last-session.md` if it exists
3. Deletes it immediately (one-shot consumption)
4. Returns JSON with `hookSpecificOutput.additionalContext` → injected into conversation context

See `references/setup-guide.md` for the full script and configuration instructions.
