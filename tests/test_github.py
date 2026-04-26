from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from darling import github


def _mock_token():
    return patch(
        "darling.github.subprocess.check_output",
        return_value="ghp_faketoken",
    )


def test_parse_pr_url_valid():
    result = github.parse_pr_url("https://github.com/owner/repo/pull/42")
    assert result == ("owner", "repo", 42)


def test_parse_pr_url_invalid():
    assert github.parse_pr_url("https://gitlab.com/owner/repo/merge_requests/1") is None
    assert github.parse_pr_url("not-a-url") is None
    assert github.parse_pr_url("https://github.com/owner/repo/issues/1") is None


def test_get_pr_status_merged():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "state": "closed",
        "merged": True,
        "title": "Fix the thing",
        "html_url": "https://github.com/owner/repo/pull/42",
    }
    mock_response.raise_for_status = MagicMock()

    with _mock_token(), patch("darling.github.httpx.get", return_value=mock_response):
        result = github.get_pr_status("owner", "repo", 42)

    assert result["merged"] is True
    assert result["state"] == "closed"
    assert result["title"] == "Fix the thing"


def test_get_pr_status_open():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "state": "open",
        "merged": False,
        "title": "WIP: new feature",
        "html_url": "https://github.com/owner/repo/pull/7",
    }
    mock_response.raise_for_status = MagicMock()

    with _mock_token(), patch("darling.github.httpx.get", return_value=mock_response):
        result = github.get_pr_status("owner", "repo", 7)

    assert result["merged"] is False
    assert result["state"] == "open"


def test_get_issue_extracts_title_and_body():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "title": "Button is broken",
        "body": "Clicking the button does nothing.",
        "number": 99,
    }
    mock_response.raise_for_status = MagicMock()

    with _mock_token(), patch("darling.github.httpx.get", return_value=mock_response):
        result = github.get_issue("https://github.com/owner/repo/issues/99")

    assert result["title"] == "Button is broken"
    assert result["number"] == 99


def test_get_issue_returns_empty_for_invalid_url():
    result = github.get_issue("https://example.com/not-an-issue")
    assert result == {}
