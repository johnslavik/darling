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

## Requirements

- [ZMX](https://github.com/johnslavik/zmx) — terminal session manager
- [gh](https://cli.github.com/) — GitHub CLI (authenticated)

## Usage

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

## Repo registry

Register your local clones so `/darling 142372` can resolve without a full URL:

```
/darling register cpython ~/Python/cpython
/darling register devguide ~/Python/devguide
```

If more than one repo is registered and the issue could belong to any of them, darling asks you to pick.

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
