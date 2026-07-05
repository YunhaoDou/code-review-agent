"""Read a file from the checked-out repo with a token-aware truncation."""
from code_review_agent.tools._safety import resolve_in_repo

TOOL_SCHEMA = {
    "name": "read_file",
    "description": (
        "Read a file by path relative to the repository root. "
        "If the file is large, returns a truncated head + tail with a note about omitted content. "
        "Use this to inspect specific files mentioned in the diff or in earlier tool results."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to repo root."},
            "max_lines": {
                "type": "integer",
                "description": "Soft cap on lines returned (default 400).",
                "default": 400,
            },
        },
        "required": ["path"],
    },
}


def run(path: str, max_lines: int = 400) -> dict:
    """Execute the tool. Returns {ok, content?, error?}."""
    p = resolve_in_repo(path)
    if p is None:
        return {"ok": False, "error": f"path escapes repository root: {path}"}
    if not p.exists():
        return {"ok": False, "error": f"file not found: {path}"}
    if not p.is_file():
        return {"ok": False, "error": f"not a file: {path}"}
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"ok": False, "error": f"read failed: {e}"}

    lines = text.split("\n")
    if len(lines) <= max_lines:
        return {"ok": True, "content": text, "truncated": False, "total_lines": len(lines)}

    head = "\n".join(lines[: max_lines // 2])
    tail = "\n".join(lines[-max_lines // 2 :])
    omitted = len(lines) - max_lines
    content = f"{head}\n\n... [{omitted} lines omitted] ...\n\n{tail}"
    return {"ok": True, "content": content, "truncated": True, "total_lines": len(lines)}
