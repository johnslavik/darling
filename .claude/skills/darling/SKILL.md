---
name: darling
description: Track in-flight development tasks across git worktrees and ZMX terminal sessions. Use when the user wants to start, resume, manage, or take inventory of in-flight work — e.g. "what are we working on", "what's the status", "where are we in terms of tasks", "list my workspaces", "what's pending", "anything queued", "work on gh-NNNNNN", "let's fix that <thing>", "open a workspace for <ref>", "darling, ...", or any reference to an issue number / GitHub issue URL. Do not trigger for general questions about an issue, code review of someone else's PR, or how-does-X-work questions unrelated to the user's own in-flight work.
---

You are the darling workspace manager. Darling tracks git worktrees + ZMX terminal sessions for in-flight development tasks.

## Invocation

Treat the user's message as the invocation. Extract the **arguments** (referred to below as `$ARGUMENTS`) as follows:

- A bare number, `gh-NNNNNN`, or `https://github.com/.../issues/NNNNNN` → the issue reference.
- A subcommand like `check`, `list`, `queue`, `repos`, `next`, `register …`, `progress …`, `tried …`, `blocker …`, `next <ws> <text…>` → that subcommand and its tail.
- Free-text task description ("work on X", "fix Y", a symbol/phrase) → pass through to **resolve-task-description**.
- Status / inventory questions ("what are we working on", "status", "what's in flight", etc.) → empty `$ARGUMENTS` (run **status**).

Then follow the dispatch table below exactly as if the user had typed `/darling $ARGUMENTS`.

---

## Dispatch

Match `$ARGUMENTS` to the first rule that applies:

| Input | Action |
|---|---|
| *(empty)* | **status** |
| `check` | **check-prs** |
| `list` | **list-workspaces** |
| `queue` | **list-queue** |
| `repos` | **list-repos** |
| `next` | **run-next-task** |
| `next <workspace_or_issue> <text...>` | **set-next-step** |
| `progress <workspace_or_issue> <text...>` | **append-progress** |
| `tried <workspace_or_issue> <text...>` | **append-tried** |
| `blocker <workspace_or_issue> <text or "none">` | **set-blocker** |
| `register <alias> <path>` | **register-repo** |
| `unregister <alias>` | **unregister-repo** |
| bare number, `gh-NNNNNN`, or `https://github.com/.../issues/NNNNNN` | **workspace-for-issue** |
| free-text task description ("work on X", "fix Y", a symbol/phrase) | **resolve-task-description** |
| anything else | ask the user what they meant |

---

## Operations

### status

Run the **Read all workspaces** snippet and the **Read queue (pending items only)** snippet. Summarise as a compact list, one block per active workspace:

```
<name>  (#<issue> · <branch> · <age>)
  next:    <next_step>
  blocker: <blockers>            # only if non-null
  tried:   <count> approaches    # only if tried is non-empty; on `/darling list` show last 1-2
  pr:      <pr_url or "—">
```

Sort by `updated_at` desc (most recently touched first), falling back to `created_at`. Then a one-line tail: `Queue: N pending`.

If `next_step` is missing or stale-looking (placeholder text from creation), flag it in the output (`next: ?? (set with /darling next ...)`) so the user knows to refresh it. Same for an empty `progress` on a workspace older than a few days.

This is the **default response when the user asks "what are we working on" / "status" / similar inventory questions** — do not fall back to `git worktree list` or `gh issue` for these; the workspace records are the source of truth.

---

### list-workspaces

Run the **Read all workspaces** snippet. Print a table: name, branch, repo, age, pr_url, next_step.

---

### list-queue

Run the **Read queue (pending items only)** snippet. Show each item's id, workspace_name, and task_prompt.

---

### list-repos

Run the **Read repos** snippet. Print alias → path pairs.

---

### register-repo

Parse `alias` and `path` from `$ARGUMENTS`. Run the **Upsert repo** snippet with those values.

---

### unregister-repo

Parse `alias` from `$ARGUMENTS`. Run the **Remove repo** snippet.

---

### check-prs

Run **Read all workspaces**. For each workspace, check both the PR (if any) and the underlying issue. If either is terminal, the workspace must be cleaned up — closed work has no in-flight workspace.

1. **PR check** — for each workspace with a non-null `pr_url`:
   - Parse owner/repo/number from the URL.
   - Run `gh pr view <number> --repo <owner>/<repo> --json state,mergedAt`.
   - If `state` is `MERGED` or `CLOSED`: queue cleanup (see below).
2. **Issue check** — for each workspace, derive the issue number from `branch` (`gh-NNNNNN-...`) and the repo from `repo_path`'s `origin` remote:
   - Run `gh issue view <number> --repo <owner>/<repo> --json state,closedAt`.
   - If `state` is `CLOSED` AND the workspace has no open PR linked: queue cleanup.

Cleanup queue prompt:

> "Workspace '<name>' is terminal (<reason: PR merged|PR closed|issue closed>). Delete the workspace: kill ZMX session '<zmx_session>', remove git worktree at '<worktree_path>', archive to knowledge base, delete branch '<branch>'."

Skip workspaces whose issue is closed but whose PR is still open — that PR may still need follow-up.

---

### set-next-step

Parse `$ARGUMENTS` as `<workspace_or_issue> <text...>`. Resolve `<workspace_or_issue>` to a workspace record (by exact `name`, or by issue number → `gh-NNNNNN-...` prefix match on `branch`). Run **Update workspace fields** with `next_step` set to the text. Print one-line confirmation.

If no workspace matches, list nearby candidates instead of guessing.

---

### append-progress

Parse `$ARGUMENTS` as `<workspace_or_issue> <text...>`. Resolve to workspace as in **set-next-step**. Run **Append to `progress`** with the text. Print one-line confirmation.

---

### append-tried

Parse `$ARGUMENTS` as `<workspace_or_issue> <text...>`. Resolve to workspace as in **set-next-step**. Run **Append to `tried`** with the text. Print one-line confirmation.

---

### set-blocker

Parse `$ARGUMENTS` as `<workspace_or_issue> <text or "none">`. Resolve to workspace as in **set-next-step**. Run **Update workspace fields** with `blockers` = text (or `null` if the text is exactly `none`). Print one-line confirmation.

---

### run-next-task

1. Run **Read queue (pending items only)**. Take the first item.
2. If none: say "Queue is empty."
3. Print the task prompt and execute it using available tools.
4. On completion: run **Mark queue item done** with the item's id and a brief outcome.

---

### resolve-task-description

User passed free text like `work on revamping sys.lazy_modules`, `fix the lazy modules thing`, `Counter dict typo`. Resolve it to a concrete issue **without asking the user** unless genuinely ambiguous — and **never demand they paste an issue number** when the keywords are enough to identify it.

The user is not a casual visitor on these issues; almost any task they describe is going to be one they authored, are assigned to, are mentioned in, or have commented on. Bias the search heavily toward issues that involve them. Only fall back to broader repo search when the involvement-scoped search comes up empty.

Search in this order — stop at the first source that yields a confident match:

1. **Active workspaces** — read `~/.local/share/darling/workspaces/*.json`, score against `description`, `branch`, `name`, `notes`, `progress`.
2. **Knowledge base** — read `~/.local/share/darling/knowledge_base/*.json` for archived workspaces (recent finished work often comes back).
3. **GitHub issues involving the user** — query each of these and merge:
   - `gh issue list --repo <owner>/<repo> --assignee @me --state all --search "<terms>" --limit 20 --json number,title,state,updatedAt,url,author`
   - `gh issue list --repo <owner>/<repo> --author @me --state all --search "<terms>" --limit 20 --json number,title,state,updatedAt,url,author`
   - `gh issue list --repo <owner>/<repo> --mentions @me --state all --search "<terms>" --limit 20 --json number,title,state,updatedAt,url,author`
   - `gh search issues --repo <owner>/<repo> --commenter=@me --state all "<terms>" --limit 20 --json number,title,state,updatedAt,url,author,repository` (covers issues the user discussed but didn't author/own)
   Apply a strong score boost to anything that matches one of these (they are by definition "issues that involve me"). Tag the candidate's source as `github-mine` so the ranking step can prefer it over generic hits.
4. **GitHub issues in the repo (broader)** — only run if step 3 returned no plausible match: `gh issue list --repo <owner>/<repo> --search "<terms>" --state all --limit 10 --json number,title,state,updatedAt,url`. Use `gh search issues` if the repo isn't determined yet.
5. **Codebase grep** — only as a tiebreaker, not a primary source. `grep -rn` the distinguishing tokens to confirm a candidate's relevance.

Run this resolver script — it returns ranked candidates as JSON:

```python
python3 - << 'EOF'
import json, pathlib, re, subprocess, sys

query = "<free_text>"
terms = [t for t in re.findall(r"[A-Za-z_][A-Za-z0-9_.]+", query) if t.lower() not in {"work","on","the","a","an","fix","do","please","revamp","revamping","update","add","change","make","for","with","to","of"}]

def score(text, terms):
    text_l = (text or "").lower()
    return sum(1 for t in terms if t.lower() in text_l)

candidates = []
seen_issue_nums = set()

def add(c):
    candidates.append(c)
    if "number" in c: seen_issue_nums.add(c["number"])

# Active workspaces
for f in pathlib.Path("~/.local/share/darling/workspaces/").expanduser().glob("*.json"):
    w = json.loads(f.read_text())
    haystack = " ".join(str(w.get(k, "") or "") for k in ("description","branch","notes","progress","next_step"))
    s = score(haystack, terms)
    if s: add({"source":"workspace","score":s,"name":w["name"],"description":w["description"],"branch":w["branch"],"pr_url":w.get("pr_url"),"created_at":w.get("created_at"),"updated_at":w.get("updated_at")})

# Knowledge base
kb = pathlib.Path("~/.local/share/darling/knowledge_base/").expanduser()
if kb.exists():
    for f in kb.glob("*.json"):
        w = json.loads(f.read_text())
        s = score(w.get("description","") + " " + w.get("branch",""), terms)
        if s: add({"source":"knowledge_base","score":s,"name":w["name"],"description":w["description"],"branch":w["branch"],"archived_at":w.get("archived_at")})

# Resolve repo
r = subprocess.run(["git","rev-parse","--show-toplevel"], capture_output=True, text=True)
owner_repo = None
if r.returncode == 0:
    r2 = subprocess.run(["git","-C",r.stdout.strip(),"remote","get-url","origin"], capture_output=True, text=True)
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", r2.stdout.strip())
    if m: owner_repo = f"{m.group(1)}/{m.group(2)}"

# GitHub issues involving the user — strong signal, big score boost
MINE_BOOST = 3
def fetch(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip(): return []
    try: return json.loads(r.stdout)
    except json.JSONDecodeError: return []

mine_results = []
if owner_repo:
    sq = " ".join(terms)
    mine_results += fetch(["gh","issue","list","--repo",owner_repo,"--assignee","@me","--state","all","--search",sq,"--limit","20","--json","number,title,state,updatedAt,url,author"])
    mine_results += fetch(["gh","issue","list","--repo",owner_repo,"--author","@me","--state","all","--search",sq,"--limit","20","--json","number,title,state,updatedAt,url,author"])
    mine_results += fetch(["gh","issue","list","--repo",owner_repo,"--mentions","@me","--state","all","--search",sq,"--limit","20","--json","number,title,state,updatedAt,url,author"])
    # commenter scoping requires `gh search issues`
    mine_results += fetch(["gh","search","issues","--repo",owner_repo,"--commenter=@me","--state","all","--limit","20","--json","number,title,state,updatedAt,url,author,repository",sq])

# Dedup by number, keep best score, mark involves_me
seen_mine = {}
for issue in mine_results:
    num = issue.get("number")
    if not num or num in seen_issue_nums: continue
    s = score(issue.get("title",""), terms)
    if not s: continue
    boosted = s + MINE_BOOST
    prev = seen_mine.get(num)
    if not prev or prev["score"] < boosted:
        seen_mine[num] = {"source":"github-mine","score":boosted,"raw_score":s,"number":num,"title":issue["title"],"state":issue["state"],"updated":issue["updatedAt"],"url":issue["url"],"involves_me":True}

for c in seen_mine.values(): add(c)

# Broader repo search — only if no "mine" hits
if owner_repo and not seen_mine:
    sq = " ".join(terms)
    for issue in fetch(["gh","issue","list","--repo",owner_repo,"--search",sq,"--state","all","--limit","10","--json","number,title,state,updatedAt,url"]):
        if issue["number"] in seen_issue_nums: continue
        s = score(issue["title"], terms)
        if s and issue["state"].upper() == "OPEN":
            add({"source":"github","score":s,"number":issue["number"],"title":issue["title"],"state":issue["state"],"updated":issue["updatedAt"],"url":issue["url"],"involves_me":False})

# Sort: score desc, then prefer workspace > github-mine > github > knowledge_base
src_rank = {"workspace":0,"github-mine":1,"github":2,"knowledge_base":3}
candidates.sort(key=lambda c: (-c["score"], src_rank.get(c.get("source"), 9)))
print(json.dumps({"query":query,"terms":terms,"owner_repo":owner_repo,"candidates":candidates[:10]}, indent=2))
EOF
```

Before deciding, **prune terminal workspaces**: for each workspace/knowledge_base candidate, run `gh issue view <num> --repo <owner>/<repo> --json state` once. If `CLOSED` (and no open linked PR), drop the candidate and queue cleanup using the **check-prs** prompt — closed work shouldn't surface as a resumable option.

Decide based on the candidate list:

- **Zero candidates** — tell the user nothing matched and show the search terms used so they can correct them. Only as a last resort ask for an issue number / URL — the user shouldn't have to look that up themselves when the keywords are descriptive.
- **One candidate, high confidence** — proceed without asking. Triggers:
  - the candidate is an active workspace, **or**
  - the candidate is a `github-mine` hit (involves the user) and no other candidate is within 1 point of it, **or**
  - top raw score ≥ 2 AND no other candidate within 1 point.
  Route to **workspace-for-issue** with the issue number. Tell the user which candidate you picked and why in one line ("picked #148587 — your assigned issue, matches `lazy_modules`").
- **Multiple candidates or low confidence** — present them and ask the user to pick. Mark `github-mine` candidates with `(yours)` so the user can spot them quickly. Format:

  > Found N candidates for `<query>`. Pick one or give an issue number:
  >
  > 1. **#148587** — Revamp `sys.lazy_modules` (open, github, score 3)
  >    https://github.com/python/cpython/issues/148587
  > 2. **#145057** — PEP 810: lazy imports tracking issue (open, github, score 2)
  >    https://github.com/python/cpython/issues/145057
  > 3. **#142800** — `sys.lazy_modules` repr is misleading (closed, github, score 2)

  Before listing, **deduplicate**: if an active/archived workspace and a github issue refer to the same issue number, merge them into one entry showing both facets (e.g. `#148587 — Revamp sys.lazy_modules (open) — active workspace gh-148587-revamp-sys-lazy-modules`). Never show the same issue twice.

  For workspace candidates, include branch + age + PR status. For github candidates, include number, title, state, last updated. For knowledge_base candidates, mark as `(archived)`.

After the user confirms, route to **workspace-for-issue** with the chosen issue number.

---

### workspace-for-issue

#### Extract — issue number and extra instructions

Parse `$ARGUMENTS` into two parts:
- **issue_ref**: the leading token(s) that identify the issue — a bare number, `gh-NNNNNN`, or a GitHub URL ending in `/issues/NNNNNN`
- **extra_instructions**: everything after the issue ref (may be empty)

Extraction rules:
- Bare number `142372` → issue_number = `142372`
- `gh-142372` or `gh-142372-some-slug` → issue_number = `142372`
- GitHub URL → extract the number after `/issues/`
- Any text following the issue ref → extra_instructions (preserve verbatim)

#### Plan — resolve everything in one shot

Run this script. It outputs a JSON plan with all values needed to decide what to do next.

```python
python3 - << 'PLAN_EOF'
import json, pathlib, re, subprocess, sys, datetime

issue_number = "<issue_number>"

# --- existing workspace? ---
ws_dir = pathlib.Path("~/.local/share/darling/workspaces/").expanduser()
all_ws = [json.loads(f.read_text()) for f in ws_dir.glob("*.json")]
existing = next((w for w in all_ws if f"gh-{issue_number}" in w["branch"] or f"#{issue_number}" in w.get("description", "")), None)

# --- repo path ---
r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
if r.returncode == 0:
    repo_path = r.stdout.strip()
    errors = []
else:
    repos_p = pathlib.Path("~/.local/share/darling/repos.json").expanduser()
    repos = json.loads(repos_p.read_text())["repos"] if repos_p.exists() else []
    if len(repos) == 1:
        repo_path = repos[0]["path"]
        errors = []
    else:
        print(json.dumps({"error": "cannot resolve repo", "repos": repos}))
        sys.exit(1)

# --- remote → owner/repo ---
r2 = subprocess.run(["git", "-C", repo_path, "remote", "get-url", "origin"], capture_output=True, text=True)
remote = r2.stdout.strip()
m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", remote)
owner, repo_name = (m.group(1), m.group(2)) if m else ("", "")

# --- fetch issue ---
if existing:
    issue = {"title": existing["description"].split(": ", 1)[-1], "number": int(issue_number), "body": ""}
else:
    r3 = subprocess.run(
        ["gh", "issue", "view", issue_number, "--repo", f"{owner}/{repo_name}", "--json", "title,number,body"],
        capture_output=True, text=True)
    issue = json.loads(r3.stdout) if r3.returncode == 0 else {"title": "", "number": int(issue_number), "body": ""}
    errors = [] if r3.returncode == 0 else [r3.stderr.strip()]

# --- derive names ---
slug = re.sub(r"[^a-z0-9]+", "-", issue["title"].lower()).strip("-")[:50]
branch = existing["branch"] if existing else f"gh-{issue_number}-{slug}"
workspace_name = branch[:60]
repo_parent = str(pathlib.Path(repo_path).parent)
worktree_path = existing["worktree_path"] if existing else f"{repo_parent}/{repo_name}-worktrees/gh-{issue_number}"

# --- zmx sessions ---
r4 = subprocess.run(["zmx", "list", "--short"], capture_output=True, text=True)
zmx_sessions = [l.strip() for l in r4.stdout.splitlines() if l.strip()]
session_exists = workspace_name in zmx_sessions

plan = {
    "action": "resume" if existing else "create",
    "issue_number": issue_number,
    "issue_title": issue["title"],
    "issue_body": issue["body"],
    "repo_path": repo_path,
    "owner": owner,
    "repo_name": repo_name,
    "branch": branch,
    "workspace_name": workspace_name,
    "worktree_path": worktree_path,
    "existing_workspace": existing,
    "session_exists": session_exists,
    "zmx_sessions": zmx_sessions,
    "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    "errors": errors,
}
print(json.dumps(plan, indent=2))
PLAN_EOF
```

Read the JSON output and proceed:

- **`action == "resume"` and `session_exists == true`**: run `zmx history <workspace_name> | tail -50` to check state. If Claude actively running → tell user and stop. If idle/finished → relaunch via `zmx run`. If broken → `zmx kill <workspace_name> --force`, then relaunch via `zmx run`.
- **`action == "resume"` and `session_exists == false`**: relaunch via `zmx run` (no worktree/record creation needed).
- **`action == "create"`**: create worktree, write record, then launch.

For **create**:

```bash
git -C <repo_path> worktree add -b <branch> <worktree_path> main
```

Write the workspace record using the **Write a workspace record** snippet with values from the plan JSON. For `next_step` on a fresh workspace, default to `"read the issue and decide on an approach"` unless the user's `extra_instructions` already imply something more concrete (e.g. "fix the off-by-one in foo.c" → `next_step` = `"fix the off-by-one in foo.c"`).

#### Refresh `next_step` whenever you learn something

Whether you just created the workspace, resumed it, or merely talked about it, end the turn by running **Update workspace fields** with a refreshed `next_step` if your understanding of the next action has changed. Cheap to overwrite, expensive to leave stale. Examples that warrant an update:

- User describes a concrete next action ("now I need to add tests for the empty-list case").
- A PR is opened or its review state changes.
- CI fails or passes on a meaningful push.
- The work is blocked on an external decision — record the blocker as `next_step`.

#### Launch Claude in the session

Compose a self-contained prompt (the receiving Claude has no memory of this conversation):

1. `"Work on issue #<number>: <title>."`
2. Issue body verbatim
3. Workspace context: repo path, branch, worktree path
4. Extra instructions verbatim (high priority — place last)
5. **Ship-it block** — paste verbatim:
   > "**Shipping is part of the job.** When you reach a meaningful checkpoint (compiles, tests pass, or the requested change is done), commit and push the topic branch — do not end the session with unpushed work. Follow the project's contribution workflow as documented in its CLAUDE.md / CLAUDE.local.md / CONTRIBUTING for the exact remote and commit style. Never force-push a published branch.
   >
   > **Do NOT open or create pull requests.** Never run `gh pr create` or any equivalent. If a PR already exists for this branch, pushing updates it — that's fine. If no PR exists, leave it that way; the user will open the PR themselves. Only open a PR if the user has explicitly asked you to in this session's instructions.
   >
   > End by reporting the commit SHA and (if a PR already existed) the PR URL."
6. `"Begin immediately. Read the project's CLAUDE.md / CLAUDE.local.md for skill instructions before starting."`

Write to temp file and launch entirely in the background — never call `zmx attach` (interactive, leaks to caller's terminal):

```bash
cat > /tmp/darling-<issue_number>.txt << 'DARLING_EOF'
<prompt content>
DARLING_EOF

zmx run <workspace_name> -d sh -c 'cd <worktree_path> && claude --allowedTools "Bash,Read,Edit,Write,Agent" < /tmp/darling-<issue_number>.txt'
```

`zmx run` creates the session if it does not exist. The `-d` flag detaches it completely — no terminal leakage.

**Now run the zmx session sanity check** (see top of file) to confirm the session is alive AND Claude is actually running. Do not skip this. Only proceed to opening the Ghostty window if the check passes.

#### Open a Ghostty window attached to the session

After delegation, open a new Ghostty window attached to the session so the user can watch.

Ghostty's `-e` runs the command without a login shell, so `$PATH` is bare and `zmx` is not found — the window flashes "Process exited". Wrap in a login shell so `~/.zshrc`/`~/.bash_profile` populate `PATH`:

```bash
open -na Ghostty.app --args -e "/bin/bash -lc 'zmx attach <workspace_name>'"
```

Tell the user:
> Delegated. New Ghostty window attached. Detach with `Ctrl+\` (keeps session running) or `zmx detach` (detaches all clients). Re-attach: `zmx attach <workspace_name>`.

**Do not ask for confirmation before creating or delegating.**

---

## Invariants

### Pipeline self-healing

The darling pipeline must work end-to-end. If any step misbehaves — Ghostty window dies immediately, `zmx attach` exits, `zmx run` does not start the intended command, the plan script errors, a Python snippet fails — **fix this skill file at `~/.claude/commands/darling.md` before reporting back**. Patch the broken instruction, document the cause inline, and proceed. Do not just route around the breakage. The user expects darling to keep itself working.

When you patch the skill, finish the user's request first if you can, then surface a one-line note about what you changed.

---

### zmx session sanity check

After every `zmx run` launch, verify the session is alive AND running the intended command. zmx silently accepts launches that exit immediately, so a "session created" message is not proof of success.

Run this immediately after `zmx run`:

```bash
sleep 2
zmx list --short | grep -qx "<workspace_name>" || echo "MISSING: session not in zmx list"
zmx history <workspace_name> 2>&1 | tail -20
```

The history tail must show evidence the intended command is running:

- For Claude launches: a Claude prompt box, "Working…", a tool call line, or the literal prompt text echoed.
- For raw shell commands: the expected stdout/banner.

If the tail shows a bare shell prompt, "Process exited", "command not found", or is empty after 2s, the launch failed. Surface the history to the user, kill the session with `zmx kill <workspace_name> --force`, fix the root cause (PATH, missing flag, bad quoting), patch this skill per **Pipeline self-healing** above, and retry once. Do not silently leave a dead session in the workspace record.

---

## State

All state lives in `~/.local/share/darling/`. Read and write it directly with the Bash tool using the Python snippets below — never construct JSON by hand.

```
~/.local/share/darling/
  workspaces/           one .json file per active workspace
  knowledge_base/       archived completed workspaces
  queue.json            pending tasks
  repos.json            registered repo aliases
```

### Workspace record shape

```json
{
  "name": "gh-142372-document-pycf",
  "description": "#142372: Document PyCF_ALLOW_INCOMPLETE_INPUT",
  "repo_path": "/Users/me/Python/cpython",
  "branch": "gh-142372-document-pycf-allow-incomplete-input",
  "worktree_path": "/Users/me/Python/cpython-worktrees/gh-142372",
  "zmx_session": "gh-142372-document-pycf",
  "pr_url": null,
  "pr_number": null,
  "pr_repo": null,
  "created_at": "<ISO 8601 UTC>",
  "updated_at": "<ISO 8601 UTC>",
  "status": "active",
  "notes": "",
  "next_step": "<one-line description of the immediate next action — e.g. 'address review comment about thread safety on PR #142400', 'rebase onto main and push', 'wait for CI on push abc123'>",
  "progress": "<free-form running summary of what's been done so far — append, don't replace>",
  "tried": [
    "<short note: approach attempted + outcome — e.g. 'tried reusing PyDict_GetItem; failed because of borrowed-ref lifetime issues'>"
  ],
  "blockers": "<current blocker, or null — e.g. 'waiting on @gpshead review', 'PEP 810 decision pending'>"
}
```

The four narrative fields (`next_step`, `progress`, `tried`, `blockers`) collectively act as the workspace's working memory. They are what makes resuming a stale workspace cheap. Treat them as living text, not metadata to fill once and forget.

- **`next_step`** — single sentence, the immediate next action. Always set. Refresh aggressively.
- **`progress`** — free-form running summary; append new bullets/sentences as work advances. Reads like a short project log.
- **`tried`** — list of one-liners, each: approach + outcome. Failed attempts go here so we don't redo them. Successful attempts can graduate into `progress`.
- **`blockers`** — what's currently stopping forward motion (review, decision, dependency, environmental). `null` when unblocked.

When unknown (just created, no plan yet), set `next_step` to something concrete like `"read the issue and decide on an approach"`; leave `progress`/`tried`/`blockers` empty/null until there's something real to record.

### repos.json shape

```json
{ "repos": [{"alias": "cpython", "path": "/Users/me/Python/cpython"}] }
```

### queue.json shape

```json
{
  "items": [
    {
      "id": "<8-char hex>",
      "task_prompt": "...",
      "workspace_name": "...",
      "status": "pending",
      "queued_at": "<ISO 8601 UTC>",
      "processed_at": null,
      "outcome": null
    }
  ]
}
```

---

## Python snippets for state operations

Use these exact snippets via the Bash tool. Substitute `<placeholders>` with real values.

### Find a workspace by issue number

```python
python3 - << 'EOF'
import json, pathlib
p = pathlib.Path("~/.local/share/darling/workspaces/").expanduser()
ws = [json.loads(f.read_text()) for f in p.glob("*.json")]
match = next((w for w in ws if "gh-<issue_number>" in w["branch"] or "#<issue_number>" in w.get("description", "")), None)
print(json.dumps(match) if match else "null")
EOF
```

### Read all workspaces

```python
python3 - << 'EOF'
import json, pathlib
p = pathlib.Path("~/.local/share/darling/workspaces/").expanduser()
ws = [json.loads(f.read_text()) for f in sorted(p.glob("*.json"))]
print(json.dumps(ws, indent=2))
EOF
```

### Write a workspace record

```python
python3 - << 'EOF'
import json, pathlib, datetime
now = datetime.datetime.utcnow().isoformat() + "Z"
record = {
    "name": "<workspace_name>",
    "description": "#<issue_number>: <issue_title>",
    "repo_path": "<repo_path>",
    "branch": "<branch>",
    "worktree_path": "<worktree_path>",
    "zmx_session": "<workspace_name>",
    "pr_url": None,
    "pr_number": None,
    "pr_repo": None,
    "created_at": now,
    "updated_at": now,
    "status": "active",
    "notes": "",
    "next_step": "<one-line next action — required>",
    "progress": "",
    "tried": [],
    "blockers": None
}
p = pathlib.Path("~/.local/share/darling/workspaces/<workspace_name>.json").expanduser()
p.write_text(json.dumps(record, indent=2))
print("written:", p)
EOF
```

### Update workspace fields (e.g. `next_step`, `progress`, `tried`, `blockers`, `pr_url`)

Use this whenever the conversation reveals new state worth persisting. Always touches `updated_at`.

```python
python3 - << 'EOF'
import json, pathlib, datetime
p = pathlib.Path("~/.local/share/darling/workspaces/<workspace_name>.json").expanduser()
record = json.loads(p.read_text())
updates = {
    # set only the fields that changed; e.g.
    # "next_step": "rebase onto main and re-push after #148999 merges",
    # "blockers": "waiting on @gpshead review of PR #148530",
    # "pr_url": "https://github.com/python/cpython/pull/148530",
    # "pr_number": 148530,
    # "pr_repo": "python/cpython",
}
record.update(updates)
record["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
p.write_text(json.dumps(record, indent=2))
print("updated:", list(updates))
EOF
```

### Append to `progress` (running log)

Don't overwrite `progress` — append. Use this to add a dated bullet.

```python
python3 - << 'EOF'
import json, pathlib, datetime
now = datetime.datetime.utcnow().isoformat() + "Z"
date = now[:10]
entry = "<short bullet — what just got done or learned>"
p = pathlib.Path("~/.local/share/darling/workspaces/<workspace_name>.json").expanduser()
record = json.loads(p.read_text())
prior = record.get("progress") or ""
record["progress"] = (prior + ("\n" if prior else "") + f"- {date}: {entry}").strip()
record["updated_at"] = now
p.write_text(json.dumps(record, indent=2))
print("appended progress")
EOF
```

### Append to `tried` (failed/attempted approaches)

```python
python3 - << 'EOF'
import json, pathlib, datetime
now = datetime.datetime.utcnow().isoformat() + "Z"
entry = "<short: approach + outcome, e.g. 'monkey-patched _Py_Dealloc; SIGSEGV under free-threaded build'>"
p = pathlib.Path("~/.local/share/darling/workspaces/<workspace_name>.json").expanduser()
record = json.loads(p.read_text())
record.setdefault("tried", []).append(entry)
record["updated_at"] = now
p.write_text(json.dumps(record, indent=2))
print("appended tried")
EOF
```

### Delete a workspace record

```bash
python3 -c "
import pathlib
p = pathlib.Path('~/.local/share/darling/workspaces/<workspace_name>.json').expanduser()
p.unlink()
print('deleted:', p)
"
```

### Archive a workspace to knowledge_base

```python
python3 - << 'EOF'
import json, pathlib, datetime
src = pathlib.Path("~/.local/share/darling/workspaces/<workspace_name>.json").expanduser()
record = json.loads(src.read_text())
record["archived_at"] = datetime.datetime.utcnow().isoformat() + "Z"
kb = pathlib.Path("~/.local/share/darling/knowledge_base/").expanduser()
kb.mkdir(parents=True, exist_ok=True)
ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
dest = kb / f"<workspace_name>-{ts}.json"
dest.write_text(json.dumps(record, indent=2))
print("archived to:", dest)
EOF
```

### Read queue (pending items only)

```python
python3 - << 'EOF'
import json, pathlib
p = pathlib.Path("~/.local/share/darling/queue.json").expanduser()
q = json.loads(p.read_text()) if p.exists() else {"items": []}
pending = [i for i in q["items"] if i["status"] == "pending"]
print(json.dumps(pending, indent=2))
EOF
```

### Append item to queue

```python
python3 - << 'EOF'
import json, pathlib, secrets, datetime
p = pathlib.Path("~/.local/share/darling/queue.json").expanduser()
q = json.loads(p.read_text()) if p.exists() else {"items": []}
q["items"].append({
    "id": secrets.token_hex(4),
    "task_prompt": "<task_prompt>",
    "workspace_name": "<workspace_name>",
    "status": "pending",
    "queued_at": datetime.datetime.utcnow().isoformat() + "Z",
    "processed_at": None,
    "outcome": None
})
p.write_text(json.dumps(q, indent=2))
print("queued:", q["items"][-1]["id"])
EOF
```

### Mark queue item done

```python
python3 - << 'EOF'
import json, pathlib, datetime
p = pathlib.Path("~/.local/share/darling/queue.json").expanduser()
q = json.loads(p.read_text())
item = next(i for i in q["items"] if i["id"] == "<item_id>")
item["status"] = "done"
item["processed_at"] = datetime.datetime.utcnow().isoformat() + "Z"
item["outcome"] = "<outcome>"
p.write_text(json.dumps(q, indent=2))
print("done:", item["id"])
EOF
```

### Read repos

```python
python3 - << 'EOF'
import json, pathlib
p = pathlib.Path("~/.local/share/darling/repos.json").expanduser()
repos = json.loads(p.read_text()) if p.exists() else {"repos": []}
print(json.dumps(repos["repos"], indent=2))
EOF
```

### Upsert repo

```python
python3 - << 'EOF'
import json, pathlib
p = pathlib.Path("~/.local/share/darling/repos.json").expanduser()
repos = json.loads(p.read_text()) if p.exists() else {"repos": []}
repos["repos"] = [r for r in repos["repos"] if r["alias"] != "<alias>"]
repos["repos"].append({"alias": "<alias>", "path": "<path>"})
p.write_text(json.dumps(repos, indent=2))
print("upserted:", "<alias>")
EOF
```

### Remove repo

```python
python3 - << 'EOF'
import json, pathlib
p = pathlib.Path("~/.local/share/darling/repos.json").expanduser()
repos = json.loads(p.read_text()) if p.exists() else {"repos": []}
repos["repos"] = [r for r in repos["repos"] if r["alias"] != "<alias>"]
p.write_text(json.dumps(repos, indent=2))
print("removed:", "<alias>")
EOF
```

### Derive slug and names from issue title

```python
python3 - << 'EOF'
import re
title = "<issue_title>"
issue_number = "<issue_number>"
slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50]
branch = f"gh-{issue_number}-{slug}"
workspace_name = branch[:60]
print(f"slug={slug}\nbranch={branch}\nworkspace_name={workspace_name}")
EOF
```

---

## Conventions

### Execution narration

Before each action, output one line:
```
→ <what and why>
```
After it completes, output the key result in one line.

---

### Worktree conventions

- Branch: `gh-<issue_number>-<slug>`
- Worktree directory: `<repo_parent>/<repo_name>-worktrees/gh-<issue_number>/`
- Workspace name == branch name (≤ 60 chars)

### Deleting a workspace

1. `zmx kill <zmx_session> --force` (ignore errors)
2. `git -C <repo_path> worktree remove --force <worktree_path>`
3. `git -C <repo_path> branch -D <branch>` (if instructed)
4. Run **Archive a workspace to knowledge_base**
5. Run **Delete a workspace record**