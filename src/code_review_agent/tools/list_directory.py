"""List a directory, filtering out junk."""
from code_review_agent.tools._safety import resolve_in_repo

IGNORE = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".next", ".turbo",
}

TOOL_SCHEMA = {
    "name": "list_directory",
    "description": (
        "List files and subdirectories under a given path. "
        "Junk directories (.git, node_modules, __pycache__, virtualenvs, build artifacts) are filtered out."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path relative to repo root.", "default": "."},
        },
    },
}


def run(path: str = ".") -> dict:
    p = resolve_in_repo(path)
    if p is None:
        return {"ok": False, "error": f"path escapes repository root: {path}"}
    if not p.exists():
        return {"ok": False, "error": f"path not found: {path}"}
    if not p.is_dir():
        return {"ok": False, "error": f"not a directory: {path}"}

    entries = []
    for child in sorted(p.iterdir()):
        if child.name in IGNORE or child.name.startswith("."):
            continue
        entries.append({
            "name": child.name,
            "type": "dir" if child.is_dir() else "file",
            "size": child.stat().st_size if child.is_file() else None,
        })
    return {"ok": True, "path": str(p), "entries": entries}
