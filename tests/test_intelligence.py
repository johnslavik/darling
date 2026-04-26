from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from darling import intelligence


def _mock_anthropic(response_text: str):
    mock_content = MagicMock()
    mock_content.text = response_text
    mock_msg = MagicMock()
    mock_msg.content = [mock_content]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_msg
    return patch("darling.intelligence.anthropic.Anthropic", return_value=mock_client)


def test_summarize_returns_claude_text():
    with _mock_anthropic("The session involved fixing an auth bug."):
        result = intelligence.summarize("some terminal output", "claude-opus-4-5")
    assert result == "The session involved fixing an auth bug."


def test_summarize_returns_default_for_empty_scrollback():
    result = intelligence.summarize("", "claude-opus-4-5")
    assert "empty" in result.lower()


def test_search_kb_returns_matching_indices():
    entries = [
        {"name": "auth-fix", "description": "Fix JWT", "scrollback_summary": "fixed auth", "notes": "", "completed_at": "2026-01-01"},
        {"name": "ui-work", "description": "Button redesign", "scrollback_summary": "updated CSS", "notes": "", "completed_at": "2026-01-02"},
        {"name": "db-migration", "description": "Migrate users table", "scrollback_summary": "ran migration", "notes": "", "completed_at": "2026-01-03"},
    ]
    with _mock_anthropic("0,2"):
        result = intelligence.search_kb(entries, "authentication and database", "claude-opus-4-5")
    assert len(result) == 2
    assert result[0]["name"] == "auth-fix"
    assert result[1]["name"] == "db-migration"


def test_search_kb_returns_empty_for_none_response():
    entries = [{"name": "x", "description": "y", "scrollback_summary": "", "notes": "", "completed_at": ""}]
    with _mock_anthropic("none"):
        result = intelligence.search_kb(entries, "something unrelated", "claude-opus-4-5")
    assert result == []


def test_search_kb_returns_empty_for_no_entries():
    result = intelligence.search_kb([], "anything", "claude-opus-4-5")
    assert result == []


def test_create_skill_returns_markdown_draft():
    entries = [
        {"name": "auth-fix", "description": "Fix JWT", "scrollback_summary": "used PyJWT", "notes": "always pin version", "pr_outcome": "merged"},
    ]
    with _mock_anthropic("## jwt-auth skill\nAlways pin PyJWT to a specific version."):
        result = intelligence.create_skill(entries, "jwt-auth", "JWT authentication", "claude-opus-4-5")
    assert "jwt-auth" in result or "PyJWT" in result


def test_create_skill_handles_empty_entries():
    with _mock_anthropic("## empty-skill\nNo past experience found."):
        result = intelligence.create_skill([], "new-skill", "something new", "claude-opus-4-5")
    assert isinstance(result, str)
    assert len(result) > 0
