# ADR-0003: DeepSeek as a second provider, via a normalizing client boundary

- Status: Accepted
- Date: 2026-07-24

## Context

[ADR-0001](0001-why-tool-use-not-langchain.md) locked the agent to Anthropic Tool Use and
explicitly called multi-provider support a non-goal. In practice, running Phase 3
(self-review against a real PR) needed an API key, and DeepSeek's was the one available —
cheaper per call, OpenAI-compatible function-calling API.

## Decision

Add DeepSeek as a second provider. `Config.provider` selects `"anthropic"` or `"deepseek"`
(default `"deepseek"`). `LLMClient` dispatches to a per-provider implementation; both are
normalized to the same response shape the agent loop already consumed:

- `response.content` — list of blocks, `{type: "text", text}` or `{type: "tool_use", name, input, id}`
- `response.stop_reason` — `"tool_use"` or anything else (end of turn)
- `response.usage.input_tokens` / `.output_tokens`

`_DeepSeekImpl` (`client.py`) translates in both directions: Anthropic-shaped tool schemas
and conversation history to OpenAI Chat Completions `tools=`/`messages=` on the way in,
`choices[0].message` (`.content`, `.tool_calls`, `.tool_calls[].function.arguments` as a JSON
string) back to the block shape above on the way out.

## Why this shape and not something else

- **`agent.py` didn't change.** The guardrails (max_steps, token budget, loop detection),
  the tool dispatch table, and every existing orchestration test in
  `tests/test_agent_loop.py` operate on the Anthropic shape and needed zero edits — they
  still pass unmodified, because the fake `LLMClient.send` responses they construct are
  exactly what `_AnthropicImpl` and `_DeepSeekImpl` both produce.
- **The alternative** — passing OpenAI-shaped messages/responses through the whole loop and
  branching on provider inside `agent.py` — would have meant two code paths through the
  guardrail logic, which is exactly the kind of duplication that hides bugs in one path and
  not the other.
- **This does not reopen ADR-0001's core decision.** No framework was added; the loop is
  still ~200 lines of hand-rolled orchestration. Only the "multi-provider is not a goal"
  tradeoff in ADR-0001 was overtaken by events.

## Tradeoffs

- `client.py` now carries real translation logic (tool schema conversion, message-history
  conversion, response normalization) instead of being a thin SDK pass-through. That
  complexity is real but contained to one file.
- Token accounting for DeepSeek uses `prompt_tokens`/`completion_tokens` from the OpenAI-shaped
  usage object — semantically equivalent to Anthropic's `input_tokens`/`output_tokens`, but not
  the same billing units. The `max_total_tokens` guardrail default (500k) was tuned against
  Anthropic pricing; it still functions as a runaway-loop cap under DeepSeek, just not a
  precisely calibrated cost cap.
- Anthropic's prompt caching (if ever adopted) has no DeepSeek equivalent wired up. Not needed
  yet — neither provider path uses caching today.

## Reference

DeepSeek API docs (OpenAI-compatible): https://api-docs.deepseek.com/
