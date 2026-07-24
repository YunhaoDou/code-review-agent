"""Centralized config loaded from environment + YAML.

Environment variables (required at runtime):
    LLM_PROVIDER         "deepseek" (default) or "anthropic"
    ANTHROPIC_API_KEY    Claude API key (required if LLM_PROVIDER=anthropic)
    DEEPSEEK_API_KEY     DeepSeek API key (required if LLM_PROVIDER=deepseek)
    GITHUB_TOKEN         GitHub token (auto-injected by Actions)
    GITHUB_REPOSITORY    e.g. "owner/repo" (Actions auto-injects)
    GITHUB_PR_NUMBER     PR to review
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel

PROVIDER_DEFAULT_MODEL = {
    "anthropic": "claude-sonnet-4-6",
    "deepseek": "deepseek-chat",
}


class Config(BaseModel):
    # Provider + API keys — only the key matching `provider` is required (see from_env).
    provider: str = "deepseek"
    anthropic_api_key: str = ""
    deepseek_api_key: str = ""
    github_token: str
    github_repository: str
    github_pr_number: int

    # Model
    model: str = "deepseek-chat"

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

        provider = os.environ.get("LLM_PROVIDER", data.get("provider", "deepseek"))
        if provider not in PROVIDER_DEFAULT_MODEL:
            raise RuntimeError(
                f"unknown provider: {provider!r} (expected one of {list(PROVIDER_DEFAULT_MODEL)})"
            )
        data["provider"] = provider
        data.setdefault("model", PROVIDER_DEFAULT_MODEL[provider])

        data["anthropic_api_key"] = os.environ.get("ANTHROPIC_API_KEY", "")
        data["deepseek_api_key"] = os.environ.get("DEEPSEEK_API_KEY", "")
        data["github_token"] = os.environ.get("GITHUB_TOKEN", "")
        data["github_repository"] = os.environ.get("GITHUB_REPOSITORY", "")
        data["github_pr_number"] = int(os.environ.get("GITHUB_PR_NUMBER", 0))

        key_field = "deepseek_api_key" if provider == "deepseek" else "anthropic_api_key"
        required = [key_field, "github_token", "github_repository"]
        for k in required:
            if not data.get(k):
                raise RuntimeError(f"missing required config: {k}")

        return cls(**data)
