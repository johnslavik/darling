from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from darling import store
from darling.config import Config
from darling.workspace import _slugify, create, delete

# ── Slugify ───────────────────────────────────────────────────────────────────


def test_slugify_basic():
    assert _slugify("Fix JWT token expiry") == "fix-jwt-token-expiry"


def test_slugify_special_chars():
    assert _slugify("Add OAuth2.0 support!") == "add-oauth20-support"


def test_slugify_truncates_long_names():
    long_desc = "a" * 100
    assert len(_slugify(long_desc)) <= 60


def test_slugify_collapses_spaces():
    assert _slugify("too   many   spaces") == "too-many-spaces"


# ── create ────────────────────────────────────────────────────────────────────


@pytest.fixture()
def config(tmp_path: Path) -> Config:
    cfg = Config(
        worktrees_dir=tmp_path / "worktrees",
        data_dir=tmp_path / "data",
    )
    return cfg


def test_create_workspace_writes_json_and_calls_git_and_zmx(config):
    with (
        patch("darling.workspace.subprocess.run") as mock_run,
        patch("darling.workspace.zmx.attach") as mock_zmx,
    ):
        ws = create(
            config,
            repo="/tmp/repo",
            branch="feat/my-feature",
            description="Add a new feature",
            base_branch="main",
        )

    # git worktree add was called
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert "git" in call_args.args[0]
    assert "worktree" in call_args.args[0]
    assert "add" in call_args.args[0]

    # zmx attach was called
    mock_zmx.assert_called_once()
    session_name = mock_zmx.call_args.args[0]
    assert session_name == ws["name"]

    # workspace JSON was written
    saved = store.read_workspace(config.data_dir, ws["name"])
    assert saved is not None
    assert saved["branch"] == "feat/my-feature"
    assert saved["status"] == "active"


def test_create_workspace_slug_from_description(config):
    with (
        patch("darling.workspace.subprocess.run"),
        patch("darling.workspace.zmx.attach"),
    ):
        ws = create(config, repo="/tmp/r", branch="b", description="Fix the login bug")
    assert ws["name"] == "fix-the-login-bug"


# ── delete ────────────────────────────────────────────────────────────────────


def test_delete_workspace_kills_zmx_and_removes_worktree_and_writes_kb(config):
    # Set up an active workspace in the store
    ws = store.new_workspace(
        name="bye-ws",
        description="Going away",
        repo_path="/tmp/repo",
        branch="bye-branch",
        worktree_path="/tmp/worktrees/bye-ws",
        zmx_session="bye-ws",
    )
    store.write_workspace(config.data_dir, ws)

    with (
        patch("darling.workspace.zmx.history", return_value="some terminal output"),
        patch("darling.workspace.zmx.kill") as mock_kill,
        patch("darling.workspace.intelligence.summarize", return_value="Did some work."),
        patch("darling.workspace.subprocess.run") as mock_run,
    ):
        delete(config, ws, delete_branch=False)

    mock_kill.assert_called_once_with("bye-ws")

    # git worktree remove was called
    git_calls = [c for c in mock_run.call_args_list if "worktree" in c.args[0]]
    assert len(git_calls) == 1

    # git branch -D was NOT called (delete_branch=False)
    branch_calls = [c for c in mock_run.call_args_list if "branch" in c.args[0]]
    assert len(branch_calls) == 0

    # workspace file removed
    assert store.read_workspace(config.data_dir, "bye-ws") is None

    # KB entry written
    kb = store.find_kb_entry(config.data_dir, "bye-ws")
    assert kb is not None
    assert kb["pr_outcome"] == "manual_delete"
    assert kb["scrollback_summary"] == "Did some work."


def test_delete_workspace_deletes_branch_when_requested(config):
    ws = store.new_workspace(
        name="rm-branch",
        description="d",
        repo_path="/tmp/r",
        branch="rm-branch",
        worktree_path="/tmp/w",
        zmx_session="rm-branch",
    )
    store.write_workspace(config.data_dir, ws)

    with (
        patch("darling.workspace.zmx.history", return_value=""),
        patch("darling.workspace.zmx.kill"),
        patch("darling.workspace.intelligence.summarize", return_value=""),
        patch("darling.workspace.subprocess.run") as mock_run,
    ):
        delete(config, ws, delete_branch=True)

    branch_calls = [c for c in mock_run.call_args_list if "branch" in c.args[0]]
    assert len(branch_calls) == 1
    assert "-D" in branch_calls[0].args[0]
    assert "rm-branch" in branch_calls[0].args[0]
