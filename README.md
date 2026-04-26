# darling

Personal MCP server for managing development workspaces.

**One workspace = one git worktree + one ZMX session + one knowledge base record.**

When you start a task, darling creates a git worktree and a ZMX terminal session together. When you're done, it kills the session, summarizes what happened via Claude, and archives everything to a searchable knowledge base. A task queue lets Claude execute cleanup and batch operations on your behalf.

## Requirements

- Python 3.14+, [uv](https://docs.astral.sh/uv/)
- [ZMX](https://github.com/johnslavik/zmx) — terminal session manager
- [gh](https://cli.github.com/) — GitHub CLI (authenticated)
- `ANTHROPIC_API_KEY` in your environment

## Install

```bash
git clone https://github.com/johnslavik/darling
cd darling
uv sync
```

Register as an MCP server in `~/.claude.json`:

```bash
claude mcp add darling -- uv run --directory /path/to/darling darling
```

## Configuration

Config is read from `~/.config/darling/config.toml`. All fields are optional:

```toml
worktrees_dir = "~/darling/workspaces"       # where git worktrees are created
data_dir      = "~/.local/share/darling"     # JSON storage (point at iCloud/Dropbox for sync)
anthropic_model = "claude-opus-4-5"
```

## Tools

### Workspace lifecycle

**`create_workspace`** — create a git worktree + ZMX session pair.

```
repo          local path to the git repository
branch        branch name to create
description   what you're working on (becomes the workspace name slug)
base_branch   branch to base the worktree on (default: main)
issue_url     optional GitHub issue URL — title is prepended to description
```

Returns the new workspace info plus related past KB entries for immediate context.

**`list_workspaces`** — show all active workspaces with name, branch, repo, linked PR, and age.

**`get_workspace`** — load a workspace by partial name/description match and get a Claude summary of the current ZMX session.

**`delete_workspace`** — kill the ZMX session, summarize the scrollback, write a KB record, remove the worktree.

```
name            partial match
delete_branch   also run git branch -D (default: false)
```

**`link_pr`** — associate a GitHub PR URL with a workspace so `check_prs` can watch it.

### Task queue

The queue holds natural-language prompts. Claude reads each one and executes it using the available tools.

**`enqueue_task`** — add any task.

```
task_prompt     what to do (natural language)
workspace_name  optional — attach context from a specific workspace
repo_paths      optional list of repo paths
reason          optional label (e.g. "pr_merged")
```

**`list_queue`** — show all pending tasks.

**`get_next_task`** — return the oldest pending task. Execute it, then call `complete_task`.

**`complete_task`** — mark a task done.

```
task_id   returned by get_next_task
outcome   optional summary of what was done
```

**`check_prs`** — poll GitHub for all workspaces with a linked PR. Merged or closed PRs are automatically enqueued as cleanup tasks.

### Knowledge base

**`add_note`** — append a retrospective note to a workspace or KB record.

**`search_history`** — natural language search across all past KB entries. Claude finds the relevant ones.

**`create_skill_from_notes`** — search the KB and ask Claude to draft a `~/.claude/commands/{skill_name}.md` skill file from matching entries. Returns the draft; you save it manually.

## Typical workflow

```
# Start a task
create_workspace repo=/code/myrepo branch=fix-auth description="Fix JWT expiry" issue_url=https://github.com/org/repo/issues/42

# Check in on it later
get_workspace fix-jwt

# Link the PR once open
link_pr workspace_name=fix-jwt-expiry pr_url=https://github.com/org/repo/pull/99

# Poll for merged PRs → enqueues cleanup automatically
check_prs

# Process the queue
get_next_task   # → read the prompt, call delete_workspace, etc.
complete_task task_id=abc123

# Search past work
search_history "JWT authentication patterns"

# Turn experience into a reusable skill
create_skill_from_notes query="JWT auth" skill_name=jwt-auth
```

## Storage

All data lives in `{data_dir}/` as versioned JSON files — no database, safe to sync via iCloud/Dropbox/dotfiles.

```
{data_dir}/
├── workspaces/
│   └── {name}.json
├── queue.json
└── knowledge_base/
    └── {name}-{timestamp}.json
```

Every file carries `"schema_version": "1.0"`. New fields are always optional with defaults, so old files are read safely by new code and vice versa.
