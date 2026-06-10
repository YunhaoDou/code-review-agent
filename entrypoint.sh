#!/bin/sh
set -e

# Fetch the PR diff from GitHub
DIFF_URL="https://api.github.com/repos/${GITHUB_REPOSITORY}/pulls/${GITHUB_PR_NUMBER}"
DIFF=$(curl -sS \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3.diff" \
  "${DIFF_URL}")

if [ -z "$DIFF" ]; then
  echo "error: empty diff for ${GITHUB_REPOSITORY}#${GITHUB_PR_NUMBER}"
  exit 1
fi

echo "Fetched $(echo "$DIFF" | wc -l) lines of diff. Running agent..."
echo "$DIFF" | code-review-agent
