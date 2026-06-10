# code-review-agent

[![Tests](https://github.com/YunhaoDou/code-review-agent/actions/workflows/test.yml/badge.svg)](https://github.com/YunhaoDou/code-review-agent/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)

> A multi-step code-review agent powered by Anthropic Tool Use. Drop it into any repo as a GitHub Action — PRs get reviewed automatically.

**Status**: Phase 0 (scaffold). Phase 1 lands the Tool Use loop.

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

| Phase | What |
|---|---|
| 0 | Scaffold + tool schemas + guardrails (done) |
| 1 | Implement Tool Use loop |
| 2 | Loop detection + token accounting |
| 3 | Self-review (dogfood: this action reviews its own PRs) |
| 4 | Publish to GitHub Marketplace |

## License

[MIT](LICENSE)
