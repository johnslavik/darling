from __future__ import annotations

import json
from pathlib import Path

import pytest

from darling import store


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "darling"
    (d / "workspaces").mkdir(parents=True)
    (d / "knowledge_base").mkdir()
    return d


# ── Schema version ────────────────────────────────────────────────────────────

def test_workspace_has_schema_version(data_dir):
    ws = store.new_workspace(
        name="test-ws",
        description="Test workspace",
        repo_path="/tmp/repo",
        branch="test-branch",
        worktree_path="/tmp/worktrees/test-ws",
        zmx_session="test-ws",
    )
    store.write_workspace(data_dir, ws)
    raw = json.loads((data_dir / "workspaces" / "test-ws.json").read_text())
    assert raw["schema_version"] == "1.0"


def test_kb_entry_has_schema_version(data_dir):
    ws = store.new_workspace(
        name="done-ws", description="Done", repo_path="/tmp/r",
        branch="b", worktree_path="/tmp/w", zmx_session="done-ws",
    )
    entry = store.new_kb_entry(ws, "raw scrollback", "summary", "merged")
    path = store.write_kb_entry(data_dir, entry)
    raw = json.loads(path.read_text())
    assert raw["schema_version"] == "1.0"


def test_queue_has_schema_version(data_dir):
    store.enqueue(data_dir, task_prompt="do something")
    raw = json.loads((data_dir / "queue.json").read_text())
    assert raw["schema_version"] == "1.0"


# ── Workspace CRUD ────────────────────────────────────────────────────────────

def test_write_and_read_workspace(data_dir):
    ws = store.new_workspace(
        name="my-feature",
        description="Add a new feature",
        repo_path="/code/repo",
        branch="feat/my-feature",
        worktree_path="/worktrees/my-feature",
        zmx_session="my-feature",
    )
    store.write_workspace(data_dir, ws)
    result = store.read_workspace(data_dir, "my-feature")
    assert result["name"] == "my-feature"
    assert result["branch"] == "feat/my-feature"
    assert result["status"] == "active"


def test_list_workspaces_returns_all(data_dir):
    for name in ("ws-a", "ws-b", "ws-c"):
        ws = store.new_workspace(
            name=name, description=name, repo_path="/r",
            branch=name, worktree_path=f"/w/{name}", zmx_session=name,
        )
        store.write_workspace(data_dir, ws)
    results = store.list_workspaces(data_dir)
    assert len(results) == 3
    assert {w["name"] for w in results} == {"ws-a", "ws-b", "ws-c"}


def test_delete_workspace_file(data_dir):
    ws = store.new_workspace(
        name="to-delete", description="d", repo_path="/r",
        branch="b", worktree_path="/w", zmx_session="to-delete",
    )
    store.write_workspace(data_dir, ws)
    assert store.read_workspace(data_dir, "to-delete") is not None
    store.delete_workspace_file(data_dir, "to-delete")
    assert store.read_workspace(data_dir, "to-delete") is None


def test_find_workspace_by_partial_name(data_dir):
    ws = store.new_workspace(
        name="fix-auth-token-expiry", description="Fix JWT expiry",
        repo_path="/r", branch="b", worktree_path="/w", zmx_session="fix-auth-token-expiry",
    )
    store.write_workspace(data_dir, ws)
    found = store.find_workspace(data_dir, "auth")
    assert found is not None
    assert found["name"] == "fix-auth-token-expiry"


def test_find_workspace_by_description(data_dir):
    ws = store.new_workspace(
        name="some-slug", description="Refactor the billing pipeline",
        repo_path="/r", branch="b", worktree_path="/w", zmx_session="some-slug",
    )
    store.write_workspace(data_dir, ws)
    found = store.find_workspace(data_dir, "billing")
    assert found is not None


def test_find_workspace_returns_none_for_no_match(data_dir):
    assert store.find_workspace(data_dir, "nonexistent") is None


def test_read_workspace_returns_none_for_missing(data_dir):
    assert store.read_workspace(data_dir, "ghost") is None


def test_old_workspace_missing_field_gets_default(data_dir):
    # Simulate a v1.0 file missing a future field — reads should not raise
    ws = store.new_workspace(
        name="old-ws", description="old", repo_path="/r",
        branch="b", worktree_path="/w", zmx_session="old-ws",
    )
    store.write_workspace(data_dir, ws)
    # Remove a field to simulate an older schema
    raw = json.loads((data_dir / "workspaces" / "old-ws.json").read_text())
    del raw["pr_url"]
    (data_dir / "workspaces" / "old-ws.json").write_text(json.dumps(raw))
    # Reading should not crash; field should be absent (caller uses .get())
    result = store.read_workspace(data_dir, "old-ws")
    assert result.get("pr_url") is None


# ── Knowledge base ────────────────────────────────────────────────────────────

def test_write_and_list_kb_entries(data_dir):
    for i in range(3):
        ws = store.new_workspace(
            name=f"ws-{i}", description=f"workspace {i}", repo_path="/r",
            branch=f"b-{i}", worktree_path=f"/w/{i}", zmx_session=f"ws-{i}",
        )
        entry = store.new_kb_entry(ws, f"scrollback {i}", f"summary {i}", "merged")
        store.write_kb_entry(data_dir, entry)
    entries = store.list_kb_entries(data_dir)
    assert len(entries) == 3


def test_kb_entry_preserves_outcome(data_dir):
    ws = store.new_workspace(
        name="closed-ws", description="d", repo_path="/r",
        branch="b", worktree_path="/w", zmx_session="closed-ws",
    )
    entry = store.new_kb_entry(ws, "raw", "summary", "closed")
    store.write_kb_entry(data_dir, entry)
    entries = store.list_kb_entries(data_dir)
    assert entries[0]["pr_outcome"] == "closed"


def test_add_note_to_kb_entry(data_dir):
    ws = store.new_workspace(
        name="noted-ws", description="d", repo_path="/r",
        branch="b", worktree_path="/w", zmx_session="noted-ws",
    )
    entry = store.new_kb_entry(ws, "raw", "summary", "merged")
    store.write_kb_entry(data_dir, entry)
    store.update_kb_notes(data_dir, "noted-ws", "This was tricky because of X")
    updated = store.find_kb_entry(data_dir, "noted-ws")
    assert "tricky" in updated["notes"]


def test_update_kb_notes_returns_false_when_not_found(data_dir):
    assert store.update_kb_notes(data_dir, "ghost", "note") is False


def test_add_workspace_note(data_dir):
    ws = store.new_workspace(
        name="active-ws", description="d", repo_path="/r",
        branch="b", worktree_path="/w", zmx_session="active-ws",
    )
    store.write_workspace(data_dir, ws)
    result = store.add_workspace_note(data_dir, "active-ws", "learned something useful")
    assert result is True
    updated = store.read_workspace(data_dir, "active-ws")
    assert "learned something useful" in updated["notes"]


def test_add_workspace_note_returns_false_when_not_found(data_dir):
    assert store.add_workspace_note(data_dir, "ghost", "note") is False


# ── Queue ─────────────────────────────────────────────────────────────────────

def test_enqueue_and_list(data_dir):
    store.enqueue(data_dir, task_prompt="clean up workspace X", workspace_name="ws-x", reason="pr_merged")
    store.enqueue(data_dir, task_prompt="bump dependencies in repo Y", repo_paths=["/repo/y"])
    items = store.list_queue(data_dir)
    assert len(items) == 2
    assert items[0]["task_prompt"] == "clean up workspace X"
    assert items[1]["repo_paths"] == ["/repo/y"]


def test_get_next_pending_returns_oldest(data_dir):
    store.enqueue(data_dir, task_prompt="first task")
    store.enqueue(data_dir, task_prompt="second task")
    next_item = store.get_next_pending(data_dir)
    assert next_item["task_prompt"] == "first task"


def test_complete_task_removes_from_pending(data_dir):
    item_id = store.enqueue(data_dir, task_prompt="do work")
    store.complete_queue_item(data_dir, item_id, outcome="done successfully")
    pending = store.list_queue(data_dir)
    assert len(pending) == 0
    all_items = store.list_queue(data_dir, include_done=True)
    assert len(all_items) == 1
    assert all_items[0]["status"] == "done"
    assert all_items[0]["outcome"] == "done successfully"


def test_complete_task_returns_false_for_unknown_id(data_dir):
    assert store.complete_queue_item(data_dir, "bad-id") is False


def test_queue_empty_returns_none(data_dir):
    assert store.get_next_pending(data_dir) is None


def test_enqueue_returns_unique_ids(data_dir):
    ids = [store.enqueue(data_dir, task_prompt=f"task {i}") for i in range(5)]
    assert len(set(ids)) == 5
