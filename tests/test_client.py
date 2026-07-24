"""Unit tests for the DeepSeek <-> Anthropic-shape normalization in client.py.

No real DEEPSEEK_API_KEY/ANTHROPIC_API_KEY needed: the SDK clients are built lazily
(see client.py) and never touched here — `chat.completions.create` is monkeypatched.
"""
from types import SimpleNamespace

from code_review_agent.client import (
    LLMClient,
    _AnthropicImpl,
    _DeepSeekImpl,
    _from_openai_response,
    _to_openai_messages,
    _to_openai_tools,
)
from code_review_agent.config import Config

READ_FILE_SCHEMA = {
    "name": "read_file",
    "description": "Read a file.",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
}


def make_config(**overrides) -> Config:
    defaults = dict(
        deepseek_api_key="test-key",
        github_token="test-token",
        github_repository="acme/widgets",
        github_pr_number=1,
    )
    defaults.update(overrides)
    return Config(**defaults)


def test_llm_client_picks_deepseek_impl_by_default():
    client = LLMClient(make_config())
    assert isinstance(client._impl, _DeepSeekImpl)


def test_llm_client_picks_anthropic_impl():
    client = LLMClient(make_config(provider="anthropic", anthropic_api_key="test-key"))
    assert isinstance(client._impl, _AnthropicImpl)


def test_to_openai_tools_converts_anthropic_schema():
    converted = _to_openai_tools([READ_FILE_SCHEMA])
    assert converted == [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file.",
                "parameters": READ_FILE_SCHEMA["input_schema"],
            },
        }
    ]


def test_to_openai_messages_handles_tool_result_and_tool_use():
    tool_use_block = SimpleNamespace(type="tool_use", name="read_file", input={"path": "a.py"}, id="t1")
    text_block = SimpleNamespace(type="text", text="checking a.py")
    messages = [
        {"role": "user", "content": "Here is the diff"},
        {"role": "assistant", "content": [text_block, tool_use_block]},
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "t1", "content": '{"ok": true}'}],
        },
    ]

    out = _to_openai_messages("system prompt", messages)

    assert out[0] == {"role": "system", "content": "system prompt"}
    assert out[1] == {"role": "user", "content": "Here is the diff"}
    assert out[2]["role"] == "assistant"
    assert out[2]["content"] == "checking a.py"
    assert out[2]["tool_calls"] == [
        {"id": "t1", "type": "function", "function": {"name": "read_file", "arguments": '{"path": "a.py"}'}}
    ]
    assert out[3] == {"role": "tool", "tool_call_id": "t1", "content": '{"ok": true}'}


def test_from_openai_response_text_only():
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="all good", tool_calls=None))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )

    normalized = _from_openai_response(response)

    assert normalized.stop_reason == "end_turn"
    assert len(normalized.content) == 1
    assert normalized.content[0].type == "text"
    assert normalized.content[0].text == "all good"
    assert normalized.usage.input_tokens == 10
    assert normalized.usage.output_tokens == 5


def test_from_openai_response_tool_call():
    call = SimpleNamespace(
        id="call_1", function=SimpleNamespace(name="grep_code", arguments='{"pattern": "TODO"}')
    )
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[call]))],
        usage=SimpleNamespace(prompt_tokens=20, completion_tokens=8),
    )

    normalized = _from_openai_response(response)

    assert normalized.stop_reason == "tool_use"
    assert len(normalized.content) == 1
    block = normalized.content[0]
    assert block.type == "tool_use"
    assert block.name == "grep_code"
    assert block.input == {"pattern": "TODO"}
    assert block.id == "call_1"


def test_deepseek_impl_send_round_trip(monkeypatch):
    """End-to-end: fake `openai` chat completion -> normalized response used by agent.py."""
    call = SimpleNamespace(
        id="call_1", function=SimpleNamespace(name="list_directory", arguments='{"path": "."}')
    )
    fake_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[call]))],
        usage=SimpleNamespace(prompt_tokens=15, completion_tokens=7),
    )

    llm = LLMClient(make_config())

    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["tools"][0]["function"]["name"] == "read_file"
            return fake_response

    class FakeChat:
        completions = FakeCompletions()

    monkeypatch.setattr(llm._impl, "_client", SimpleNamespace(chat=FakeChat()))

    result = llm.send(system="sys", messages=[{"role": "user", "content": "diff"}], tools=[READ_FILE_SCHEMA])

    assert result.stop_reason == "tool_use"
    assert result.content[0].name == "list_directory"
    assert result.usage.input_tokens == 15
