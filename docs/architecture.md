# Architecture

```
┌────────────────────────────────────┐
│  GitHub Pull Request               │
└──────────────┬─────────────────────┘
               │ pull_request event
               ▼
┌────────────────────────────────────┐
│  GitHub Actions runner             │
│  uses: YunhaoDou/code-review-agent │
└──────────────┬─────────────────────┘
               │ launches Docker container
               ▼
┌────────────────────────────────────┐
│  entrypoint.sh                     │
│  • fetches PR diff via GH API      │
│  • pipes diff to agent CLI         │
└──────────────┬─────────────────────┘
               ▼
┌────────────────────────────────────┐
│  agent.run_agent(diff, config)     │
│  • initial Tool Use call to Claude │
│  • loop:                           │
│      LLM decides next tool         │
│      run tool                      │
│      feed result back              │
│      check guardrails              │
│  • emit final summary              │
└──────────────┬─────────────────────┘
               │ writes PR comments
               ▼
       GitHub Pull Request
```

## Three guardrails

| Guardrail | Limit | Where |
|---|---|---|
| max_steps | 15 tool calls | agent loop |
| token budget | 500k total | per response check |
| loop detection | same tool 3× in a row → halt | dispatch table |

The first two are set in `config.py`. The third is inline in `agent.py` Phase 1.

## Tool design philosophy

Each tool has:
- A **description** written for the LLM (not the human) — it's the docs Claude reads to pick the right tool
- A strict **input_schema** in JSON Schema form
- An implementation that returns a `dict` with `{ok, ...}`

The implementations stay small. Composition is the LLM's job, not the tool's.

## What we deliberately don't do

| Pattern | Why not |
|---|---|
| LangChain / LangGraph | Anthropic's Tool Use is enough for 5 tools. LangChain adds dependencies and abstractions for problems we don't have. |
| Vector embedding over the codebase | Phase 1 doesn't need it; we use `grep_code` + `read_file`. |
| Auto-apply fixes (write to PR branch) | One step too far. Comments are reversible; commits are not. |
| Multiple LLM providers | Lock to Claude for clarity; add adapters later if needed. |
