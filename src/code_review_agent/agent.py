"""Main agent loop: orchestrates Claude Tool Use against a PR diff.

Three guardrails, checked every turn (see docs/architecture.md):
  1. max_steps      — hard cap on LLM round-trips
  2. token budget   — per-turn input cap + cumulative total across the run
  3. loop detection — same (tool, args) signature repeated back to back
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

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

# Loop-detection guardrail: this many identical (tool, args) calls in a row halts the run.
LOOP_WINDOW = 3


class GuardrailViolation(Exception):
    """Raised when the agent loop hits a safety guardrail."""

    def __init__(self, guardrail: str, message: str) -> None:
        self.guardrail = guardrail
        super().__init__(message)


def _tool_signature(name: str, tool_input: dict) -> str:
    return f"{name}:{json.dumps(tool_input, sort_keys=True, default=str)}"


def _dispatch_tool(name: str, tool_input: dict) -> dict:
    if name not in TOOLS:
        return {"ok": False, "error": f"unknown tool: {name}"}
    _, impl = TOOLS[name]
    try:
        return impl(**tool_input)
    except TypeError as e:
        return {"ok": False, "error": f"bad arguments for {name}: {e}"}
    except Exception as e:  # noqa: BLE001 — a buggy tool must not crash the whole review run
        return {"ok": False, "error": f"{name} raised: {e}"}


def run_agent(diff: str, config: Config) -> dict:
    """Execute the full Tool Use loop against a PR diff and return a summary."""
    llm = LLMClient(config)
    tool_schemas = [schema for schema, _ in TOOLS.values()]

    messages: list[dict] = [
        {"role": "user", "content": f"Here is the PR diff to review:\n\n{diff}"}
    ]

    steps = 0
    total_tokens = 0
    call_signatures: list[str] = []
    comments_posted = 0
    nudged = False

    while True:
        if steps >= config.max_steps:
            raise GuardrailViolation("max_steps", f"exceeded max_steps={config.max_steps}")

        response = llm.send(system=SYSTEM_PROMPT, messages=messages, tools=tool_schemas)
        steps += 1

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "output_tokens", 0) if usage else 0

        if input_tokens > config.max_input_tokens:
            raise GuardrailViolation(
                "max_input_tokens",
                f"single turn used {input_tokens} tokens > max_input_tokens={config.max_input_tokens}",
            )

        total_tokens += input_tokens + output_tokens
        if total_tokens > config.max_total_tokens:
            raise GuardrailViolation(
                "token_budget",
                f"cumulative usage {total_tokens} > max_total_tokens={config.max_total_tokens}",
            )

        if response.content:
            # Skip appending a genuinely empty assistant turn (no text, no tool call) —
            # some providers produce these (see nudge below), and OpenAI-compatible APIs
            # reject an assistant message with neither content nor tool_calls set.
            messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            summary = "".join(
                block.text for block in response.content if getattr(block, "type", None) == "text"
            )
            if comments_posted == 0 and not summary.strip() and not nudged:
                # Some providers occasionally end a turn with empty content and no tool
                # call after a run of tool_use steps (observed with DeepSeek). One nudge
                # back into the loop, rather than silently returning nothing.
                nudged = True
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "You stopped without posting anything. Call post_review_comment "
                            "exactly once now: a specific issue you found, or a summary saying "
                            "the PR looks clean."
                        ),
                    }
                )
                continue
            return {
                "ok": True,
                "steps": steps,
                "total_tokens": total_tokens,
                "comments_posted": comments_posted,
                "summary": summary,
            }

        tool_results = []
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue

            signature = _tool_signature(block.name, block.input)
            call_signatures.append(signature)
            if len(call_signatures) >= LOOP_WINDOW and len(set(call_signatures[-LOOP_WINDOW:])) == 1:
                raise GuardrailViolation(
                    "loop_detection",
                    f"'{block.name}' called {LOOP_WINDOW}x in a row with identical arguments",
                )

            result = _dispatch_tool(block.name, block.input)
            if block.name == "post_review_comment" and result.get("ok"):
                comments_posted += 1

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                }
            )

        messages.append({"role": "user", "content": tool_results})


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

    try:
        result = run_agent(diff, config)
    except GuardrailViolation as e:
        print(f"error: guardrail '{e.guardrail}' triggered: {e}", file=sys.stderr)
        sys.exit(2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
