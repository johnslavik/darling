from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from darling import zmx


def test_attach_calls_zmx_with_session_and_cwd():
    with patch("darling.zmx.subprocess.run") as mock_run:
        zmx.attach("my-session", Path("/tmp/work"))
        mock_run.assert_called_once_with(
            ["zmx", "attach", "my-session"],
            cwd=Path("/tmp/work"),
            check=True,
        )


def test_kill_calls_zmx_kill_with_force():
    with patch("darling.zmx.subprocess.run") as mock_run:
        zmx.kill("my-session")
        mock_run.assert_called_once_with(
            ["zmx", "kill", "my-session", "--force"],
            check=False,
        )


def test_history_returns_last_n_lines():
    output = "\n".join(f"line {i}" for i in range(50))
    with patch("darling.zmx.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=output, returncode=0)
        result = zmx.history("my-session", lines=10)
    lines = result.splitlines()
    assert len(lines) == 10
    assert lines[-1] == "line 49"


def test_history_returns_empty_for_no_output():
    with patch("darling.zmx.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = zmx.history("dead-session")
    assert result == ""


def test_history_returns_all_lines_when_fewer_than_limit():
    output = "line 1\nline 2\nline 3"
    with patch("darling.zmx.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=output, returncode=0)
        result = zmx.history("my-session", lines=100)
    assert result == output
