from __future__ import annotations

from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from darling import github, intelligence, store, workspace, zmx
from darling.config import load_config

mcp = FastMCP("darling")
_config = load_config()


def _format_kb_entry(e: dict) -> dict:
    return {
        "name": e.get("name"),
        "description": e.get("description"),
        "summary": e.get("scrollback_summary"),
        "outcome": e.get("pr_outcome"),
        "pr_url": e.get("pr_url"),
        "date": e.get("completed_at", "")[:10],
        "notes": e.get("notes"),
    }


def _search_kb(query: str) -> list[dict]:
    entries = store.list_kb_entries(_config.data_dir)
    if not entries:
        return []
    return intelligence.search_kb(entries, query, _config.anthropic_model)


# ── Workspace lifecycle ───────────────────────────────────────────────────────

@mcp.tool()
def create_workspace(
    repo: str,
    branch: str,
    description: str,
    base_branch: str = "main",
    issue_url: str = "",
) -> dict:
    """Create a git worktree + ZMX session pair. Returns workspace info and
    related KB entries for immediate context."""
    if issue_url:
        try:
            issue = github.get_issue(issue_url)
            if issue.get("title"):
                prefix = f"#{issue['number']}: {issue['title']}"
                description = f"{prefix} — {description}" if description else prefix
        except Exception:
            pass

    ws = workspace.create(
        _config,
        repo=repo,
        branch=branch,
        description=description,
        base_branch=base_branch,
    )

    return {
        "workspace": ws,
        "related_past_experiences": [_format_kb_entry(e) for e in _search_kb(description)],
    }


@mcp.tool()
def list_workspaces() -> list[dict]:
    """List all active workspaces."""
    results = []
    for ws in store.list_workspaces(_config.data_dir):
        age = ""
        created = ws.get("created_at", "")
        if created:
            try:
                delta = datetime.now(timezone.utc) - datetime.fromisoformat(created)
                age = f"{delta.days}d" if delta.days else f"{delta.seconds // 3600}h"
            except Exception:
                pass
        results.append({
            "name": ws.get("name"),
            "description": ws.get("description"),
            "branch": ws.get("branch"),
            "repo": ws.get("repo_path"),
            "pr_url": ws.get("pr_url"),
            "age": age,
            "status": ws.get("status"),
        })
    return results


@mcp.tool()
def get_workspace(name: str) -> dict:
    """Get workspace details and a Claude summary of the current ZMX session.
    Accepts partial name or description match."""
    ws = store.find_workspace(_config.data_dir, name)
    if not ws:
        return {"error": f"No workspace matching '{name}'"}

    scrollback = zmx.history(ws.get("zmx_session", ws["name"]))
    return {
        "workspace": ws,
        "session_summary": intelligence.summarize(scrollback, _config.anthropic_model),
    }


@mcp.tool()
def delete_workspace(name: str, delete_branch: bool = False) -> dict:
    """Delete a workspace: kill ZMX session, remove worktree, save scrollback to KB."""
    ws = store.find_workspace(_config.data_dir, name)
    if not ws:
        return {"error": f"No workspace matching '{name}'"}
    return workspace.delete(_config, ws, delete_branch=delete_branch)


@mcp.tool()
def link_pr(workspace_name: str, pr_url: str) -> dict:
    """Associate a GitHub PR URL with a workspace so check_prs can watch it."""
    ws = store.find_workspace(_config.data_dir, workspace_name)
    if not ws:
        return {"error": f"No workspace matching '{workspace_name}'"}

    parsed = github.parse_pr_url(pr_url)
    if not parsed:
        return {"error": f"Could not parse GitHub PR URL: {pr_url}"}

    owner, repo, number = parsed
    ws["pr_url"] = pr_url
    ws["pr_number"] = number
    ws["pr_repo"] = f"{owner}/{repo}"
    store.write_workspace(_config.data_dir, ws)
    return {"linked": pr_url, "workspace": ws["name"]}


# ── Task queue ────────────────────────────────────────────────────────────────

_CLEANUP_PROMPT = (
    "Workspace '{name}' (branch: {branch}, repo: {repo}) had its PR {outcome}. "
    "Clean it up completely: kill ZMX session '{zmx_session}', remove the git "
    "worktree at '{worktree_path}', delete the topic branch '{branch}', save a "
    "scrollback summary to the knowledge base, and remove any other files or "
    "artifacts that were created specifically while working on this task."
)


@mcp.tool()
def enqueue_task(
    task_prompt: str,
    workspace_name: str = "",
    repo_paths: list[str] | None = None,
    reason: str = "",
) -> dict:
    """Add any natural-language task to the queue. Claude will execute it via
    get_next_task. Use this for one-off or batch operations across repos."""
    item_id = store.enqueue(
        _config.data_dir,
        task_prompt=task_prompt,
        workspace_name=workspace_name or None,
        repo_paths=repo_paths,
        reason=reason or None,
    )
    return {"queued": item_id, "task_prompt": task_prompt}


@mcp.tool()
def list_queue() -> list[dict]:
    """List all pending tasks in the queue."""
    return store.list_queue(_config.data_dir)


@mcp.tool()
def get_next_task() -> dict:
    """Return the next pending task. Execute it using other darling tools, then
    call complete_task with the task id."""
    item = store.get_next_pending(_config.data_dir)
    if not item:
        return {"message": "Queue is empty."}

    ws_context = {}
    if item.get("workspace_name"):
        ws = store.find_workspace(_config.data_dir, item["workspace_name"])
        if ws:
            ws_context = ws

    return {
        "task_id": item["id"],
        "task_prompt": item["task_prompt"],
        "workspace": ws_context,
        "repo_paths": item.get("repo_paths", []),
        "reason": item.get("reason"),
        "queued_at": item.get("queued_at"),
    }


@mcp.tool()
def complete_task(task_id: str, outcome: str = "") -> dict:
    """Mark a queue task as completed after you've executed it."""
    ok = store.complete_queue_item(_config.data_dir, task_id, outcome or None)
    if not ok:
        return {"error": f"Task '{task_id}' not found"}
    return {"completed": task_id}


@mcp.tool()
def check_prs() -> dict:
    """Check GitHub PR status for all workspaces with a linked PR.
    Merged/closed PRs are automatically added to the cleanup queue."""
    workspaces = store.list_workspaces(_config.data_dir)
    enqueued = []
    errors = []
    checked = 0

    for ws in workspaces:
        pr_url = ws.get("pr_url")
        pr_number = ws.get("pr_number")
        pr_repo = ws.get("pr_repo")

        if not (pr_url and pr_number and pr_repo):
            continue

        checked += 1
        owner, repo = pr_repo.split("/", 1)
        try:
            status = github.get_pr_status(owner, repo, int(pr_number))
        except Exception as e:
            errors.append({"workspace": ws["name"], "error": str(e)})
            continue

        if status["merged"] or status["state"] == "closed":
            outcome = "merged" if status["merged"] else "closed"
            prompt = _CLEANUP_PROMPT.format(
                name=ws["name"],
                branch=ws["branch"],
                repo=pr_repo,
                outcome=outcome,
                zmx_session=ws.get("zmx_session", ws["name"]),
                worktree_path=ws["worktree_path"],
            )
            item_id = store.enqueue(
                _config.data_dir,
                task_prompt=prompt,
                workspace_name=ws["name"],
                reason=f"pr_{outcome}",
            )
            enqueued.append({"workspace": ws["name"], "task_id": item_id, "outcome": outcome})

    return {"enqueued": enqueued, "errors": errors, "checked": checked}


# ── Knowledge base ────────────────────────────────────────────────────────────

@mcp.tool()
def add_note(workspace_name: str, note: str) -> dict:
    """Add a retrospective note to a workspace's knowledge base record."""
    if store.update_kb_notes(_config.data_dir, workspace_name, note):
        return {"updated": workspace_name, "storage": "knowledge_base"}
    if store.add_workspace_note(_config.data_dir, workspace_name, note):
        return {"updated": workspace_name, "storage": "workspace"}
    return {"error": f"No workspace or KB entry matching '{workspace_name}'"}


@mcp.tool()
def search_history(query: str) -> list[dict]:
    """Search the knowledge base with a natural language query. Claude finds
    relevant past workspace records."""
    return [_format_kb_entry(e) for e in _search_kb(query)]


@mcp.tool()
def create_skill_from_notes(query: str, skill_name: str) -> dict:
    """Search KB for relevant experiences and ask Claude to draft a
    ~/.claude/commands/{skill_name}.md skill file from them."""
    relevant = _search_kb(query)
    draft = intelligence.create_skill(relevant, skill_name, query, _config.anthropic_model)
    return {
        "skill_name": skill_name,
        "suggested_path": f"~/.claude/commands/{skill_name}.md",
        "draft": draft,
        "based_on": [e.get("name") for e in relevant],
    }
