# darling

Claude skill for managing development workspaces.

**One workspace = one git worktree + one ZMX session.**

Invoke `/darling` from Claude with an issue number or GitHub URL to open a workspace. Darling creates the git worktree, starts a ZMX session, and tracks everything in `~/.local/share/darling/`.

## Install

```bash
git clone https://github.com/johnslavik/darling
ln -sf ~/OSS/darling/.claude/commands/darling.md ~/.claude/commands/darling.md
```

The symlink makes `/darling` available globally in Claude Code. Since it's a symlink, edits to the skill file in the repo take effect immediately.

Then add the following to `~/.claude/CLAUDE.md` (create the file if it doesn't exist) so Claude knows when to invoke darling automatically — without needing the `/darling` prefix:

```markdown
## Darling workspace manager

Darling is a workspace manager for development tasks. Its skill is installed at `~/.claude/commands/darling.md`.

Invoke the darling skill whenever the user's intent is to **start, resume, or manage work on a specific GitHub issue or development task** — regardless of whether they use the word "darling" or the `/darling` command. Examples that should trigger it:

- "work on gh-142372"
- "let's fix that cpython issue"
- "open a workspace for the devguide ticket"
- "darling, 142372"
- any message where the user clearly wants to begin or check in on a concrete piece of work tied to a repo or issue

When invoked this way, treat the issue reference (number, URL, or description) as `$ARGUMENTS` and follow the skill instructions exactly as if the user had typed `/darling <ref>`.

Do **not** trigger darling for general questions about an issue ("what does gh-142372 say?"), code review, or anything where the user isn't starting/managing hands-on work.
```

## Requirements

- [ZMX](https://github.com/johnslavik/zmx) — terminal session manager
- [gh](https://cli.github.com/) — GitHub CLI (authenticated)

## Usage

With the CLAUDE.md entry in place, you can invoke darling naturally:

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
```

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

The skill lives at `.claude/commands/darling.md`. Edit it there — changes are live immediately via the symlink.
