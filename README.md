# code-review-agent

[![Tests](https://github.com/YunhaoDou/code-review-agent/actions/workflows/test.yml/badge.svg)](https://github.com/YunhaoDou/code-review-agent/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)

> A multi-step code-review agent powered by Anthropic Tool Use. Drop it into any repo as a GitHub Action — PRs get reviewed automatically.

**Status**: Tool Use loop + guardrails implemented and unit-tested (Phases 0-2). Not yet run against a live PR or published to Marketplace — see [Roadmap](#roadmap).

## What it does

When a PR opens or updates, the agent:

1. Fetches the diff from GitHub
2. Reads relevant files, greps the codebase, optionally runs tests
3. Identifies real issues (logic bugs, security issues, missing tests)
4. Posts focused review comments — inline on the diff or top-level on the PR

Three guardrails keep it from running away:

- max 15 tool calls per PR
- 500k total token budget
- loop detection (same tool repeated → halt)

## Why it exists

LLMs are good at spotting obvious bugs and missing edge cases. The bottleneck for using them in code review is not intelligence — it's plumbing: fetching the diff, exploring the repo, posting comments back.

This agent is that plumbing, kept small enough to read in one sitting.

## Use it in your repo

Add `.github/workflows/code-review.yml`:

```yaml
name: Code Review
on:
  pull_request:
    types: [opened, synchronize]

permissions:
  pull-requests: write
  contents: read

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: YunhaoDou/code-review-agent@v1
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

Add `ANTHROPIC_API_KEY` to your repo's secrets. Open a PR. The agent comments within ~1 minute.

Full usage in [docs/usage.md](docs/usage.md).

## Tools the agent has

| Tool | What it does |
|---|---|
| `read_file` | Read a file, with smart head+tail truncation for long files |
| `list_directory` | List files / subdirs, junk filtered |
| `grep_code` | Regex search with ripgrep |
| `run_tests` | Execute test suite, return summary + failures |
| `post_review_comment` | Post a review comment (inline or top-level) |

## Architecture

[docs/architecture.md](docs/architecture.md) has the diagram, module boundaries, and design rationale.

## Design decisions

- [ADR-0001: Anthropic Tool Use directly, no LangChain](docs/adr/0001-why-tool-use-not-langchain.md)
- [ADR-0002: Comments only, never commits](docs/adr/0002-comments-not-commits.md)

## Roadmap

| Phase | What | Status |
|---|---|---|
| 0 | Scaffold + tool schemas + guardrails | ✅ done |
| 1 | Tool Use loop wired to the 5 tools | ✅ done, unit-tested with a mocked Anthropic client |
| 2 | Loop detection + token accounting | ✅ done — `max_steps`, per-turn + cumulative token budget, identical-call loop detection, all with tests proving they actually trigger |
| 3 | Self-review (dogfood: this action reviews its own PRs) | ☐ open — needs a real `ANTHROPIC_API_KEY` + a real PR, neither available in dev |
| 4 | Publish to GitHub Marketplace | ☐ open — repo needs to be public under the real GitHub account; not done here |

**What's genuinely unverified**: the loop has never made a real call to the Anthropic API (no key available in this environment) or posted a comment to a real GitHub PR (no live `GITHUB_TOKEN`/PR). Everything up through the orchestration logic, guardrails, and tool implementations is real code, exercised by real tests — but the live path (Phase 3) needs your credentials to prove end-to-end.

To try it for real:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GITHUB_TOKEN=ghp_...
export GITHUB_REPOSITORY=owner/repo
export GITHUB_PR_NUMBER=123
curl -sS -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3.diff" \
  "https://api.github.com/repos/$GITHUB_REPOSITORY/pulls/$GITHUB_PR_NUMBER" \
  | code-review-agent
```

Marketplace publish checklist (not executed — needs your GitHub identity):
1. Push this repo to a public `YunhaoDou/code-review-agent` on GitHub
2. Tag a release (`v1.0.0`) matching the `@v1` reference in the usage example above
3. On the release page, check "Publish this Action to the GitHub Marketplace"
4. Pick the `check-circle`/green branding category (already set in `action.yml`)

## License

[MIT](LICENSE)
