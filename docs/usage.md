# Usage

## In another repo (as a GitHub Action)

1. Add this to `.github/workflows/code-review.yml`:

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

2. Add `ANTHROPIC_API_KEY` to the repo's secrets.
3. Open a PR — the agent posts comments within ~1 minute.

## Optional config

Drop `.github/code-review-agent.yml` in your repo to customize:

```yaml
model: claude-sonnet-4-6
max_steps: 15
focus_areas:
  - logic bugs
  - security issues
  - missing tests
  - naming inconsistencies
  - obvious performance concerns
skip_focus_areas:
  - style nitpicks
  - trivial typos
```

## Local development (without GitHub)

```bash
pip install -e ".[dev]"

export ANTHROPIC_API_KEY=sk-...
export GITHUB_TOKEN=ghp_...
export GITHUB_REPOSITORY=owner/repo
export GITHUB_PR_NUMBER=123

# Pipe a diff from any source
git diff main..feature-branch | code-review-agent
```
