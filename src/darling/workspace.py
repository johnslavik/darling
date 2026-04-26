from __future__ import annotations

import re
import subprocess
from pathlib import Path

from darling import intelligence, store, zmx
from darling.config import Config


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:60].strip("-")


def create(
    config: Config,
    *,
    repo: str,
    branch: str,
    description: str,
    base_branch: str = "main",
) -> dict:
    repo_path = Path(repo).expanduser().resolve()
    name = _slugify(description)
    worktree_path = config.worktrees_dir / name

    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree_path), base_branch],
        cwd=repo_path,
        check=True,
    )

    zmx.attach(name, worktree_path)

    ws = store.new_workspace(
        name=name,
        description=description,
        repo_path=str(repo_path),
        branch=branch,
        worktree_path=str(worktree_path),
        zmx_session=name,
    )
    store.write_workspace(config.data_dir, ws)
    return ws


def delete(config: Config, ws: dict, delete_branch: bool = False) -> dict:
    name = ws["name"]
    session = ws.get("zmx_session", name)
    worktree_path = Path(ws["worktree_path"])
    repo_path = Path(ws["repo_path"])
    branch = ws["branch"]

    scrollback = zmx.history(session)
    zmx.kill(session)

    summary = intelligence.summarize(scrollback, config.anthropic_model)

    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree_path)],
        cwd=repo_path,
        check=False,
    )

    if delete_branch:
        subprocess.run(
            ["git", "branch", "-D", branch],
            cwd=repo_path,
            check=False,
        )

    pr_outcome = "manual_delete"
    kb_entry = store.new_kb_entry(ws, scrollback, summary, pr_outcome)
    kb_path = store.write_kb_entry(config.data_dir, kb_entry)
    store.delete_workspace_file(config.data_dir, name)

    return {"deleted": name, "kb_entry": str(kb_path), "summary": summary}
