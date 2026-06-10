"""Run the repo's test suite, capture failures.

We intentionally only return failures + summary, not the full stdout,
to keep agent context small.
"""
import subprocess

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
        out = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout_seconds
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"tests timed out after {timeout_seconds}s"}

    return {
        "ok": True,
        "exit_code": out.returncode,
        "passed": out.returncode == 0,
        "stdout_tail": out.stdout[-2000:],
        "stderr_tail": out.stderr[-1000:],
    }
