# ADR-0001: Anthropic Tool Use directly, no LangChain

- Status: Accepted
- Date: 2026-06-11

## Context

The agent needs a way to compose 5 tools (read_file, list_directory, grep_code, run_tests, post_review_comment) with an LLM that decides which to call.

## Options

1. Anthropic SDK's native Tool Use — JSON schemas + a `tool_use` content block
2. LangChain agents — abstraction over multiple providers
3. LangGraph — graph-based agent orchestration
4. Roll our own from scratch (no framework, raw API)

## Decision

Option 1: Anthropic Tool Use directly.

## Reasons

- **5 tools is small**. LangChain's abstractions pay off at 20+ tools or multi-provider deployments. We have neither.
- **Anthropic SDK is already a dependency**. Adding LangChain doubles install size and complicates Dockerfile.
- **Debuggability**: when something goes wrong, the trace is "agent called read_file, got X, called Y". With LangChain it becomes "agent → AgentExecutor → ToolExecutor → CallbackManager → ..." — too many layers.
- **Lock-in is a feature here**. The README explicitly says "Claude only". Multi-provider support is not a goal.
- **Phase 1 implementation is ~200 lines**. LangChain port would be ~80 lines but with 50MB of dependencies behind it.

## Tradeoffs

- If we later need to swap LLM providers, we will rewrite the agent loop. Acceptable.
  - **Amended by [ADR-0003](0003-deepseek-provider-adapter.md)**: we added a second provider
    (DeepSeek) without rewriting the loop — the translation lives entirely in `client.py`,
    which normalizes both providers to the same response shape `agent.py` already expected.
    The "no framework" decision above still holds; only the "multi-provider is not a goal"
    tradeoff was wrong.
- If the tool count grows beyond 10, we may revisit. But we'll likely split into specialized agents instead.

## Reference

Anthropic Tool Use docs: https://docs.anthropic.com/en/docs/tool-use
