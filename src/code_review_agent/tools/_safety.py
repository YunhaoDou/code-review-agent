"""Shared path-safety helper: keep tool filesystem access inside the repo root.

`path` arguments are chosen by the LLM, whose behavior is steered by
untrusted PR diff content. Without this check, a crafted diff could try to
get the agent to read files outside the checked-out repo (e.g. `../../.ssh/id_rsa`).
"""
from pathlib import Path


def resolve_in_repo(path: str, repo_root: Path | None = None) -> Path | None:
    """Resolve `path` relative to the repo root, rejecting escapes.

    Returns None if the resolved path falls outside repo_root, whether via
    `..` segments or an absolute path pointing elsewhere.
    """
    root = (repo_root or Path.cwd()).resolve()
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate
