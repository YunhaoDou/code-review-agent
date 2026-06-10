"""Centralized config loaded from environment + YAML.

Environment variables (required at runtime):
    ANTHROPIC_API_KEY    Claude API key
    GITHUB_TOKEN         GitHub token (auto-injected by Actions)
    GITHUB_REPOSITORY    e.g. "owner/repo" (Actions auto-injects)
    GITHUB_PR_NUMBER     PR to review
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel


class Config(BaseModel):
    # API
    anthropic_api_key: str
    github_token: str
    github_repository: str
    github_pr_number: int

    # Model
    model: str = "claude-sonnet-4-6"

    # Agent runtime guardrails
    max_steps: int = 15
    max_input_tokens: int = 200_000
    max_total_tokens: int = 500_000

    # Review focus (configurable via YAML)
    focus_areas: list[str] = [
        "logic bugs", "security issues", "missing tests",
        "naming inconsistencies", "obvious performance concerns",
    ]
    skip_focus_areas: list[str] = ["style nitpicks", "trivial typos"]

    @classmethod
    def from_env(cls, yaml_path: Path | None = None) -> "Config":
        data: dict = {}
        if yaml_path and yaml_path.exists():
            data = yaml.safe_load(yaml_path.read_text()) or {}

        data["anthropic_api_key"] = os.environ.get("ANTHROPIC_API_KEY", "")
        data["github_token"] = os.environ.get("GITHUB_TOKEN", "")
        data["github_repository"] = os.environ.get("GITHUB_REPOSITORY", "")
        data["github_pr_number"] = int(os.environ.get("GITHUB_PR_NUMBER", 0))

        required = ["anthropic_api_key", "github_token", "github_repository"]
        for k in required:
            if not data.get(k):
                raise RuntimeError(f"missing required config: {k}")

        return cls(**data)
