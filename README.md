# darling

Claude skill for managing development workspaces.

**One workspace = one git worktree + one ZMX session.**

Invoke `/darling` from Claude with an issue number or GitHub URL to open a workspace. Darling creates the git worktree, starts a ZMX session, and tracks everything in `~/.local/share/darling/`.

## Install

Darling ships as an **agent skill** (not a slash command), so it autoloads in any compatible agent (Claude Code, Copilot CLI, etc.) based on the `description` field in `SKILL.md` — no `CLAUDE.md` glue required.

```bash
git clone https://github.com/johnslavik/darling ~/OSS/darling
ln -sf ~/OSS/darling/.claude/skills/darling ~/.claude/skills/darling
```

The symlink installs the skill globally. Because it's a symlink to the repo, edits to `SKILL.md` take effect immediately.

To verify autoload, start a fresh agent session and ask "what are we working on" — the agent should pick up darling automatically. Explicit invocation also works (`/darling`, "darling, …", etc.) for any agent that surfaces skills via slash commands.

## Requirements

- [ZMX](https://github.com/johnslavik/zmx) — terminal session manager
- [gh](https://cli.github.com/) — GitHub CLI (authenticated)

## Usage

Darling autoloads from its skill description, so you can invoke it naturally:

```
work on gh-142372
let's fix that cpython issue
open a workspace for issue #142372
darling, what's active?
```

Or explicitly with the slash command:

```
/darling                          show active workspaces + queue
/darling 142372                   open (or find) workspace for issue #142372
/darling gh-142372                same
/darling https://github.com/...   same, with full URL
/darling list                     list workspaces
/darling queue                    list pending tasks
/darling repos                    list registered repos
/darling register cpython ~/Python/cpython
/darling check                    poll GitHub PRs → enqueue cleanup
/darling next                     run next queued task
/darling next <ws> <text...>      set the "next step" note on a workspace
/darling progress <ws> <text...>  append a dated bullet to the running log
/darling tried <ws> <text...>     append a "tried X, got Y" entry
/darling blocker <ws> <text>      set current blocker (`none` to clear)
```

## Workspace state — narrative fields

Each workspace record carries four narrative fields that together act as its working memory. They are what makes resuming a stale workspace cheap:

| Field | Shape | Purpose |
|---|---|---|
| `next_step` | string | Single sentence: the immediate next action on resume. Always set. |
| `progress` | string (multi-line) | Running log of what's been done, append-only. |
| `tried` | list of strings | Approaches attempted and their outcomes — failed attempts go here so you don't redo them. |
| `blockers` | string or null | What's currently stopping forward motion (review, decision, dependency). |

The `status` operation surfaces them first. They're meant to be refreshed continuously — every meaningful action in or about a workspace should end with updating whichever fields changed (and `updated_at`). Stale fields defeat the whole point. Use the `/darling next|progress|tried|blocker` verbs to update them explicitly, or rely on Claude to refresh them as the conversation moves.

## Repo resolution

When you give darling a bare issue number, it resolves the repo by:

1. **Current directory** — if you're inside a git repo, that's the one. No config needed.
2. **Registry fallback** — if cwd isn't a git repo, darling checks `~/.local/share/darling/repos.json`. Register clones with `/darling register <alias> <path>`. If multiple match, darling asks you to pick.

## Conventions

| Thing | Convention |
|---|---|
| Branch | `gh-<number>-<slug>` |
| Worktree | `<repo_parent>/<repo_name>-worktrees/gh-<number>/` |
| Workspace name | same as branch |

Example: issue #142372 in `~/Python/cpython` →
- branch: `gh-142372-document-pycf-allow-incomplete-input`
- worktree: `~/Python/cpython-worktrees/gh-142372/`

## State

All state is JSON files in `~/.local/share/darling/` — no database, safe to sync via iCloud/Dropbox.

```
~/.local/share/darling/
  workspaces/           active workspace records
  knowledge_base/       archived completed workspaces
  queue.json            pending tasks
  repos.json            registered repo aliases
```

## Skill source

The skill lives at `.claude/skills/darling/SKILL.md`. Edit it there — changes are live immediately via the symlink.
