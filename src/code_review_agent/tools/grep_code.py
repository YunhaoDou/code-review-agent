"""Code search via ripgrep with regex support."""
import subprocess

TOOL_SCHEMA = {
    "name": "grep_code",
    "description": (
        "Search for a regex pattern across the repository using ripgrep. "
        "Returns matches with file path, line number, and matched text. "
        "Limit results to avoid flooding context."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern (rg-flavored)."},
            "file_type": {"type": "string", "description": "Optional rg --type filter, e.g. 'py' or 'ts'."},
            "max_matches": {"type": "integer", "description": "Cap on match count.", "default": 50},
        },
        "required": ["pattern"],
    },
}


def run(pattern: str, file_type: str | None = None, max_matches: int = 50) -> dict:
    cmd = ["rg", "--no-heading", "--line-number", "--column", "--max-count", str(max_matches)]
    if file_type:
        cmd += ["--type", file_type]
    cmd.append(pattern)

    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except FileNotFoundError:
        return {"ok": False, "error": "ripgrep (rg) not installed in this environment"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "search timed out (>20s)"}

    if out.returncode == 1:
        return {"ok": True, "matches": [], "count": 0}
    if out.returncode != 0:
        return {"ok": False, "error": out.stderr.strip() or "ripgrep failed"}

    lines = [line for line in out.stdout.split("\n") if line]
    matches = []
    for line in lines[:max_matches]:
        parts = line.split(":", 3)
        if len(parts) >= 4:
            matches.append({"path": parts[0], "line": int(parts[1]), "column": int(parts[2]), "text": parts[3]})
    return {"ok": True, "matches": matches, "count": len(matches)}
