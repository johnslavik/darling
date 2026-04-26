from __future__ import annotations

import re
import subprocess

import httpx

_token_cache: str | None = None


def _token() -> str:
    global _token_cache
    if _token_cache is None:
        _token_cache = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    return _token_cache


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_pr_status(owner: str, repo: str, number: int) -> dict:
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}"
    response = httpx.get(url, headers=_headers())
    response.raise_for_status()
    data = response.json()
    return {
        "state": data.get("state"),
        "merged": data.get("merged", False),
        "title": data.get("title"),
        "html_url": data.get("html_url"),
    }


def get_issue(url: str) -> dict:
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/issues/(\d+)", url)
    if not match:
        return {}
    owner, repo, number = match.groups()
    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
    response = httpx.get(api_url, headers=_headers())
    response.raise_for_status()
    data = response.json()
    return {
        "title": data.get("title", ""),
        "body": data.get("body", ""),
        "number": data.get("number"),
    }


def parse_pr_url(url: str) -> tuple[str, str, int] | None:
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", url)
    if not match:
        return None
    owner, repo, number = match.groups()
    return owner, repo, int(number)
