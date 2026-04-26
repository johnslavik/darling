from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


# ── Workspaces ──────────────────────────────────────────────────────────────

def workspace_path(data_dir: Path, name: str) -> Path:
    return data_dir / "workspaces" / f"{name}.json"


def read_workspace(data_dir: Path, name: str) -> dict | None:
    path = workspace_path(data_dir, name)
    if not path.exists():
        return None
    return _read(path)


def write_workspace(data_dir: Path, ws: dict) -> None:
    ws["schema_version"] = SCHEMA_VERSION
    _write(workspace_path(data_dir, ws["name"]), ws)


def delete_workspace_file(data_dir: Path, name: str) -> None:
    path = workspace_path(data_dir, name)
    if path.exists():
        path.unlink()


def list_workspaces(data_dir: Path) -> list[dict]:
    ws_dir = data_dir / "workspaces"
    result = []
    for f in sorted(ws_dir.glob("*.json")):
        result.append(_read(f))
    return result


def new_workspace(
    *,
    name: str,
    description: str,
    repo_path: str,
    branch: str,
    worktree_path: str,
    zmx_session: str,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "description": description,
        "repo_path": repo_path,
        "branch": branch,
        "worktree_path": worktree_path,
        "zmx_session": zmx_session,
        "pr_url": None,
        "pr_number": None,
        "pr_repo": None,
        "created_at": _now(),
        "status": "active",
    }


def find_workspace(data_dir: Path, query: str) -> dict | None:
    query_lower = query.lower()
    for ws in list_workspaces(data_dir):
        name = ws.get("name", "")
        desc = ws.get("description", "")
        if query_lower in name.lower() or query_lower in desc.lower():
            return ws
    return None


# ── Knowledge base ───────────────────────────────────────────────────────────

def write_kb_entry(data_dir: Path, entry: dict) -> Path:
    entry["schema_version"] = SCHEMA_VERSION
    name = entry["name"]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = data_dir / "knowledge_base" / f"{name}-{ts}.json"
    _write(path, entry)
    return path


def list_kb_entries(data_dir: Path) -> list[dict]:
    kb_dir = data_dir / "knowledge_base"
    result = []
    for f in sorted(kb_dir.glob("*.json"), reverse=True):
        result.append(_read(f))
    return result


def find_kb_entry(data_dir: Path, workspace_name: str) -> dict | None:
    kb_dir = data_dir / "knowledge_base"
    matches = sorted(kb_dir.glob(f"{workspace_name}-*.json"), reverse=True)
    if matches:
        return _read(matches[0])
    return None


def update_kb_notes(data_dir: Path, workspace_name: str, note: str) -> bool:
    kb_dir = data_dir / "knowledge_base"
    matches = sorted(kb_dir.glob(f"{workspace_name}-*.json"), reverse=True)
    if not matches:
        return False
    path = matches[0]
    entry = _read(path)
    existing = entry.get("notes", "")
    entry["notes"] = (existing + "\n\n" + note).strip()
    _write(path, entry)
    return True


def new_kb_entry(ws: dict, scrollback_raw: str, scrollback_summary: str, pr_outcome: str | None) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "name": ws.get("name"),
        "description": ws.get("description"),
        "repo": ws.get("pr_repo") or ws.get("repo_path"),
        "branch": ws.get("branch"),
        "pr_url": ws.get("pr_url"),
        "pr_outcome": pr_outcome,
        "scrollback_summary": scrollback_summary,
        "scrollback_raw": scrollback_raw,
        "notes": "",
        "created_at": ws.get("created_at"),
        "completed_at": _now(),
    }


# ── Queue ────────────────────────────────────────────────────────────────────

def _queue_path(data_dir: Path) -> Path:
    return data_dir / "queue.json"


def _load_queue(data_dir: Path) -> dict:
    path = _queue_path(data_dir)
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "items": []}
    return _read(path)


def _save_queue(data_dir: Path, queue: dict) -> None:
    queue["schema_version"] = SCHEMA_VERSION
    _write(_queue_path(data_dir), queue)


def enqueue(
    data_dir: Path,
    *,
    task_prompt: str,
    workspace_name: str | None = None,
    repo_paths: list[str] | None = None,
    reason: str | None = None,
) -> str:
    queue = _load_queue(data_dir)
    item_id = str(uuid.uuid4())[:8]
    queue["items"].append({
        "id": item_id,
        "task_prompt": task_prompt,
        "workspace_name": workspace_name,
        "repo_paths": repo_paths or [],
        "reason": reason,
        "queued_at": _now(),
        "processed_at": None,
        "outcome": None,
        "status": "pending",
    })
    _save_queue(data_dir, queue)
    return item_id


def list_queue(data_dir: Path, include_done: bool = False) -> list[dict]:
    queue = _load_queue(data_dir)
    items = queue.get("items", [])
    if not include_done:
        items = [i for i in items if i.get("status") == "pending"]
    return items


def get_next_pending(data_dir: Path) -> dict | None:
    items = list_queue(data_dir)
    return items[0] if items else None


def complete_queue_item(data_dir: Path, item_id: str, outcome: str | None = None) -> bool:
    queue = _load_queue(data_dir)
    for item in queue.get("items", []):
        if item["id"] == item_id:
            item["status"] = "done"
            item["processed_at"] = _now()
            item["outcome"] = outcome
            _save_queue(data_dir, queue)
            return True
    return False
