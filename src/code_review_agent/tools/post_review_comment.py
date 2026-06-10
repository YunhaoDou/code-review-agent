"""Post a review comment on the target PR via GitHub REST API."""
from __future__ import annotations

import os
from typing import Optional

import httpx

TOOL_SCHEMA = {
    "name": "post_review_comment",
    "description": (
        "Post a review comment on the PR. Use sparingly — one comment per real issue. "
        "Optional file/line target makes it an inline comment on the diff; omit them to post a top-level comment."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "body": {"type": "string", "description": "Markdown body of the comment."},
            "path": {"type": "string", "description": "File path for inline comment (optional)."},
            "line": {"type": "integer", "description": "Line number for inline comment (optional)."},
        },
        "required": ["body"],
    },
}


def run(body: str, path: Optional[str] = None, line: Optional[int] = None) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    pr = os.environ.get("GITHUB_PR_NUMBER")
    if not (token and repo and pr):
        return {"ok": False, "error": "GITHUB_TOKEN / REPOSITORY / PR_NUMBER not set"}

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    if path and line is not None:
        url = f"https://api.github.com/repos/{repo}/pulls/{pr}/comments"
        payload = {"body": body, "path": path, "line": line, "side": "RIGHT"}
    else:
        url = f"https://api.github.com/repos/{repo}/issues/{pr}/comments"
        payload = {"body": body}

    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        return {"ok": True, "comment_id": r.json().get("id")}
    except Exception as e:
        return {"ok": False, "error": str(e)}
