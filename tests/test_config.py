from __future__ import annotations

from pathlib import Path

import pytest

from darling.config import Config, load_config


def test_default_config_paths_expand():
    cfg = Config()
    assert not str(cfg.worktrees_dir).startswith("~")
    assert not str(cfg.data_dir).startswith("~")


def test_config_creates_directories(tmp_path):
    cfg = Config(
        worktrees_dir=tmp_path / "worktrees",
        data_dir=tmp_path / "data",
    )
    assert (tmp_path / "worktrees").exists()
    assert (tmp_path / "data").exists()
    assert (tmp_path / "data" / "workspaces").exists()
    assert (tmp_path / "data" / "knowledge_base").exists()


def test_load_config_returns_defaults_when_no_file(monkeypatch, tmp_path):
    monkeypatch.setattr("darling.config.CONFIG_PATH", tmp_path / "nonexistent.toml")
    # Override dirs to avoid touching the real filesystem
    monkeypatch.setattr(
        "darling.config.Config.__post_init__",
        lambda self: None,
    )
    cfg = load_config()
    assert cfg.anthropic_model == "claude-opus-4-5"


def test_load_config_reads_toml(tmp_path, monkeypatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        'worktrees_dir = "/tmp/my-worktrees"\n'
        'data_dir = "/tmp/my-data"\n'
        'anthropic_model = "claude-haiku-4-5-20251001"\n'
    )
    monkeypatch.setattr("darling.config.CONFIG_PATH", config_file)
    monkeypatch.setattr("darling.config.Config.__post_init__", lambda self: None)
    cfg = load_config()
    assert str(cfg.worktrees_dir) == "/tmp/my-worktrees"
    assert cfg.anthropic_model == "claude-haiku-4-5-20251001"
