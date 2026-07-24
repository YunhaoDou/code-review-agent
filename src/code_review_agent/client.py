"""LLM client: dispatches to Anthropic or DeepSeek, normalizes both to one shape.

agent.py and its tests are written against the Anthropic Messages API shape:
    response.content     — list of blocks: {type: "text", text} | {type: "tool_use", name, input, id}
    response.stop_reason  — "tool_use" when the model wants to call a tool, anything else = done
    response.usage.input_tokens / .output_tokens

DeepSeek's API is OpenAI-compatible Chat Completions, shaped differently (choices[0].message
with .content / .tool_calls, finish_reason, usage.prompt_tokens/.completion_tokens). The
DeepSeek path below translates in both directions at the client boundary, so agent.py, the
tool dispatch table, and the existing orchestration tests need no changes regardless of
provider. See docs/adr/0003-deepseek-provider-adapter.md.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import anthropic
import openai

from code_review_agent.config import Config

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class LLMClient:
    def __init__(self, config: Config) -> None:
        self.config = config
        if config.provider == "anthropic":
            self._impl: Any = _AnthropicImpl(config)
        elif config.provider == "deepseek":
            self._impl = _DeepSeekImpl(config)
        else:
            raise ValueError(f"unknown provider: {config.provider!r}")

    def send(self, system: str, messages: list[dict], tools: list[dict]) -> Any:
        """One LLM round-trip. Returns a response normalized to the Anthropic shape."""
        return self._impl.send(system, messages, tools)


class _AnthropicImpl:
    """Builds the SDK client lazily so construction never requires a real API key —
    tests monkeypatch `LLMClient.send` and never exercise the SDK client itself."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client: anthropic.Anthropic | None = None

    def send(self, system: str, messages: list[dict], tools: list[dict]) -> Any:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self._config.anthropic_api_key)
        return self._client.messages.create(
            model=self._config.model,
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=4096,
        )


class _DeepSeekImpl:
    """Builds the SDK client lazily — same rationale as `_AnthropicImpl`."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client: openai.OpenAI | None = None

    def send(self, system: str, messages: list[dict], tools: list[dict]) -> Any:
        if self._client is None:
            self._client = openai.OpenAI(
                api_key=self._config.deepseek_api_key, base_url=DEEPSEEK_BASE_URL
            )
        response = self._client.chat.completions.create(
            model=self._config.model,
            messages=_to_openai_messages(system, messages),
            tools=_to_openai_tools(tools),
            max_tokens=4096,
        )
        return _from_openai_response(response)


def _to_openai_tools(tools: list[dict]) -> list[dict]:
    """Anthropic-shaped tool schemas ({name, description, input_schema}) -> OpenAI function tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in tools
    ]


def _to_openai_messages(system: str, messages: list[dict]) -> list[dict]:
    """Anthropic-shaped conversation history -> OpenAI chat messages.

    `messages` mixes: {"role": "user", "content": str}, {"role": "assistant",
    "content": [<Anthropic SDK content blocks>]}, and {"role": "user", "content":
    [{"type": "tool_result", "tool_use_id", "content"}, ...]} — see agent.py.
    """
    out: list[dict] = [{"role": "system", "content": system}]
    for m in messages:
        role, content = m["role"], m["content"]

        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue

        if content and isinstance(content[0], dict) and content[0].get("type") == "tool_result":
            for block in content:
                out.append(
                    {
                        "role": "tool",
                        "tool_call_id": block["tool_use_id"],
                        "content": block["content"],
                    }
                )
            continue

        # assistant turn made of Anthropic SDK content blocks (text / tool_use)
        text_parts = [b.text for b in content if getattr(b, "type", None) == "text"]
        tool_calls = [
            {
                "id": b.id,
                "type": "function",
                "function": {"name": b.name, "arguments": json.dumps(b.input)},
            }
            for b in content
            if getattr(b, "type", None) == "tool_use"
        ]
        assistant_msg: dict = {"role": "assistant", "content": "\n".join(text_parts) or None}
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        out.append(assistant_msg)

    return out


def _from_openai_response(response: Any) -> SimpleNamespace:
    """OpenAI ChatCompletion -> Anthropic-shaped response for agent.py to consume."""
    message = response.choices[0].message

    blocks: list[Any] = []
    if message.content:
        blocks.append(SimpleNamespace(type="text", text=message.content))
    for call in message.tool_calls or []:
        try:
            tool_input = json.loads(call.function.arguments) if call.function.arguments else {}
        except json.JSONDecodeError:
            tool_input = {}
        blocks.append(
            SimpleNamespace(type="tool_use", name=call.function.name, input=tool_input, id=call.id)
        )

    stop_reason = "tool_use" if message.tool_calls else "end_turn"
    usage = response.usage
    return SimpleNamespace(
        content=blocks,
        stop_reason=stop_reason,
        usage=SimpleNamespace(
            input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
        ),
    )
