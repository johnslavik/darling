from __future__ import annotations

import anthropic

_client = anthropic.Anthropic()


def summarize(scrollback: str, model: str) -> str:
    if not scrollback.strip():
        return "Empty session — no activity recorded."
    msg = _client.messages.create(
        model=model,
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": (
                    "Below is terminal scrollback from a development session. "
                    "Write a concise 2-4 sentence summary of what was worked on, "
                    "what was accomplished, and any notable issues or outcomes.\n\n"
                    f"<scrollback>\n{scrollback[-8000:]}\n</scrollback>"
                ),
            }
        ],
    )
    return msg.content[0].text


def search_kb(entries: list[dict], query: str, model: str) -> list[dict]:
    if not entries:
        return []
    summaries = "\n\n".join(
        f"[{i}] name={e.get('name')} date={e.get('completed_at', '')[:10]}\n"
        f"description: {e.get('description')}\n"
        f"summary: {e.get('scrollback_summary', '')[:300]}\n"
        f"notes: {e.get('notes', '')[:200]}"
        for i, e in enumerate(entries)
    )
    msg = _client.messages.create(
        model=model,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": (
                    f'Find entries most relevant to: "{query}"\n\n'
                    f"Entries:\n{summaries}\n\n"
                    "Reply with only a comma-separated list of indices (e.g. 0,3,7). "
                    "Return at most 5. If nothing is relevant, reply with: none"
                ),
            }
        ],
    )
    text = msg.content[0].text.strip()
    if text.lower() == "none":
        return []
    try:
        parts = [x.strip() for x in text.split(",")]
        indices = [int(x) for x in parts if x.isdigit()]
        return [entries[i] for i in indices if 0 <= i < len(entries)]
    except Exception:
        return []


def create_skill(entries: list[dict], skill_name: str, query: str, model: str) -> str:
    if not entries:
        context = "No relevant past experience found in the knowledge base."
    else:
        context = "\n\n".join(
            f"## Past experience: {e.get('name')}\n"
            f"**Description:** {e.get('description')}\n"
            f"**Summary:** {e.get('scrollback_summary', '')}\n"
            f"**Notes:** {e.get('notes', '')}\n"
            f"**Outcome:** {e.get('pr_outcome', 'unknown')}"
            for e in entries
        )
    msg = _client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Create a Claude Code skill file for the skill '{skill_name}' "
                    f"based on past experiences related to: {query}\n\n"
                    "The skill file is a markdown file that will be saved as "
                    f"~/.claude/commands/{skill_name}.md and invoked as /{skill_name} "
                    "in Claude Code. It should encode the lessons learned as a "
                    "reusable procedure or checklist.\n\n"
                    f"Past experiences from knowledge base:\n{context}\n\n"
                    "Write only the markdown content of the skill file, starting with a "
                    "brief description of what the skill does."
                ),
            }
        ],
    )
    return msg.content[0].text
