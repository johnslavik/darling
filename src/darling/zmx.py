from __future__ import annotations

import subprocess
from pathlib import Path


def attach(session: str, cwd: Path) -> None:
    subprocess.run(
        ["zmx", "attach", session],
        cwd=cwd,
        check=True,
    )


def kill(session: str) -> None:
    subprocess.run(["zmx", "kill", session, "--force"], check=False)


def history(session: str, lines: int = 200) -> str:
    result = subprocess.run(
        ["zmx", "history", session],
        capture_output=True,
        text=True,
        check=False,
    )
    raw = result.stdout
    if not raw:
        return ""
    return "\n".join(raw.splitlines()[-lines:])
