from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


CONFIG_PATH = Path("~/.config/darling/config.toml").expanduser()


@dataclass
class Config:
    worktrees_dir: Path = field(default_factory=lambda: Path("~/darling/workspaces").expanduser())
    data_dir: Path = field(default_factory=lambda: Path("~/.local/share/darling").expanduser())
    anthropic_model: str = "claude-opus-4-5"

    def __post_init__(self) -> None:
        self.worktrees_dir = Path(self.worktrees_dir).expanduser()
        self.data_dir = Path(self.data_dir).expanduser()
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "workspaces").mkdir(exist_ok=True)
        (self.data_dir / "knowledge_base").mkdir(exist_ok=True)


def load_config() -> Config:
    if not CONFIG_PATH.exists():
        return Config()
    with open(CONFIG_PATH, "rb") as f:
        raw = tomllib.load(f)
    return Config(
        worktrees_dir=Path(raw.get("worktrees_dir", "~/darling/workspaces")),
        data_dir=Path(raw.get("data_dir", "~/.local/share/darling")),
        anthropic_model=raw.get("anthropic_model", "claude-opus-4-5"),
    )
