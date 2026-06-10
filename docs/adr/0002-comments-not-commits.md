# ADR-0002: Comments only, never commits

- Status: Accepted
- Date: 2026-06-11

## Context

LLM-based code review tools fall into two camps:

1. **Suggesters** — post review comments, human applies fixes (us)
2. **Fixers** — write code, push commits or open new PRs

## Decision

This agent only posts comments. It will not push commits.

## Reasons

- **Reversibility**. A wrong comment is annoying; a wrong commit is data loss waiting to happen.
- **Trust ramp**. Users adopt agents that suggest before agents that act. Build trust before adding write power.
- **Authorship clarity**. Code attributed to a bot makes git blame harder to use.
- **Liability**. If our agent writes a security bug, it's our reputation. If we suggest one and the human ignores the warning, that's on them.

## Tradeoffs

- We provide less value per run than auto-fix tools
- Adoption may be slower than "magic" alternatives

## When to revisit

If user demand for auto-fix grows, add it as a separate, opt-in tool (`apply_fix`) with hard guardrails: only single-file edits, only on draft PRs, require human approval before push.
