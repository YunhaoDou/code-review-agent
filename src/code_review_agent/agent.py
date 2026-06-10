"""Main agent loop.

Phase 0 skeleton: scaffolds the tool dispatch table and guardrails.
Phase 1 fills in the actual Anthropic Tool Use loop.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from code_review_agent import __version__
from code_review_agent.client import LLMClient
from code_review_agent.config import Config
from code_review_agent.tools import (
    grep_code,
    list_directory,
    post_review_comment,
    read_file,
    run_tests,
)

# Dispatch table: tool name → (schema, implementation)
TOOLS: dict[str, tuple[dict, Any]] = {
    "read_file": (read_file.TOOL_SCHEMA, read_file.run),
    "list_directory": (list_directory.TOOL_SCHEMA, list_directory.run),
    "grep_code": (grep_code.TOOL_SCHEMA, grep_code.run),
    "run_tests": (run_tests.TOOL_SCHEMA, run_tests.run),
    "post_review_comment": (post_review_comment.TOOL_SCHEMA, post_review_comment.run),
}

SYSTEM_PROMPT = """\
You are a code review agent. You will be given the diff of a GitHub pull request.
Use the provided tools to investigate the codebase, run tests if useful, and post
review comments for any real issues you find.

Focus on: logic bugs, security issues, missing tests, naming inconsistencies,
obvious performance concerns. Skip: style nitpicks, trivial typos.

Be specific. Cite file paths and line numbers. Do not post more than 5 comments per PR.
If the PR looks clean, post one summary comment saying so and stop.
"""


class GuardrailViolation(Exception):
    """Raised when the agent loop hits a safety guardrail."""


def run_agent(diff: str, config: Config) -> dict:
    """Execute the agent loop.

    Phase 0: validates wiring + returns a dry-run result.
    Phase 1: implements the real Tool Use ↔ tool execution loop.
    """
    llm = LLMClient(config)
    tool_schemas = [schema for schema, _ in TOOLS.values()]

    # Phase 0: confirm wiring without burning API tokens
    return {
        "ok": True,
        "phase": "0-scaffold",
        "config": {
            "model": config.model,
            "max_steps": config.max_steps,
            "tools_registered": list(TOOLS),
            "repo": config.github_repository,
            "pr": config.github_pr_number,
        },
        "note": "Phase 1 fills in the Tool Use loop. See docs/architecture.md.",
    }


def main() -> None:
    """CLI entry point: read PR diff from stdin or file, run agent."""
    config = Config.from_env(yaml_path=Path(".github/code-review-agent.yml"))

    if len(sys.argv) > 1:
        diff = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        diff = sys.stdin.read()

    if not diff.strip():
        print("error: no diff provided. Pass a file path or pipe diff to stdin.", file=sys.stderr)
        sys.exit(1)

    result = run_agent(diff, config)
    print(result)


if __name__ == "__main__":
    main()
