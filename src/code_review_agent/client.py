"""Thin wrapper around the Anthropic client used by the agent loop."""
from __future__ import annotations

from typing import Any

import anthropic

from code_review_agent.config import Config


class LLMClient:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    def send(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
    ) -> Any:
        """One LLM round-trip. Returns the raw response object."""
        return self._client.messages.create(
            model=self.config.model,
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=4096,
        )
