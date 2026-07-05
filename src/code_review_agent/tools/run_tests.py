"""Run the repo's test suite, capture failures.

We intentionally only return failures + summary, not the full stdout,
to keep agent context small.
"""
import shlex
import subprocess

# `command` is LLM-chosen, and LLM behavior is steered by untrusted PR diff
# content. Restrict to known test-runner binaries and exec argv-style (no
# shell=True) so diff-injected shell metacharacters (`;`, `&&`, `$()`,
# backticks) can't do anything beyond invoking one of these binaries.
ALLOWED_BINARIES = {
    "pytest", "python", "python3", "npm", "npx", "yarn", "pnpm",
    "go", "mvn", "gradle", "./gradlew",
}

TOOL_SCHEMA = {
    "name": "run_tests",
    "description": (
        "Execute the project's test suite. Returns pass/fail counts and the first N failures. "
        "Use sparingly — this is expensive."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Test command to run, e.g. 'pytest -q' or 'npm test'.",
                "default": "pytest -q",
            },
            "timeout_seconds": {"type": "integer", "description": "Hard timeout.", "default": 60},
        },
    },
}


def run(command: str = "pytest -q", timeout_seconds: int = 60) -> dict:
    try:
        argv = shlex.split(command)
    except ValueError as e:
        return {"ok": False, "error": f"could not parse command: {e}"}

    if not argv or argv[0] not in ALLOWED_BINARIES:
        bad = argv[0] if argv else command
        return {"ok": False, "error": f"command not allowed: {bad!r}"}

    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout_seconds)
    except FileNotFoundError:
        return {"ok": False, "error": f"binary not found: {argv[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"tests timed out after {timeout_seconds}s"}

    return {
        "ok": True,
        "exit_code": out.returncode,
        "passed": out.returncode == 0,
        "stdout_tail": out.stdout[-2000:],
        "stderr_tail": out.stderr[-1000:],
    }
