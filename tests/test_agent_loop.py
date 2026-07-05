"""Orchestration tests for the Tool Use loop, against a mocked Anthropic client.

No real ANTHROPIC_API_KEY is available in this environment, so `LLMClient.send`
is monkeypatched to return canned responses shaped like the real Anthropic SDK's
Message objects (`.content` blocks with `.type`/`.text` or `.type`/`.name`/`.input`/`.id`,
and `.usage.input_tokens`/`.output_tokens`).
"""
from types import SimpleNamespace

import pytest

from code_review_agent.agent import GuardrailViolation, run_agent
from code_review_agent.client import LLMClient
from code_review_agent.config import Config


def make_config(**overrides) -> Config:
    defaults = dict(
        anthropic_api_key="test-key",
        github_token="test-token",
        github_repository="acme/widgets",
        github_pr_number=1,
    )
    defaults.update(overrides)
    return Config(**defaults)


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def tool_use_block(name, tool_input, id_):
    return SimpleNamespace(type="tool_use", name=name, input=tool_input, id=id_)


def fake_response(content, stop_reason, input_tokens=100, output_tokens=50):
    return SimpleNamespace(
        content=content,
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def test_agent_loop_happy_path(monkeypatch):
    scripted = [
        fake_response([tool_use_block("list_directory", {"path": "."}, "t1")], "tool_use"),
        fake_response([tool_use_block("post_review_comment", {"body": "LGTM"}, "t2")], "tool_use"),
        fake_response([text_block("Reviewed. No issues found.")], "end_turn"),
    ]
    calls = iter(scripted)
    monkeypatch.setattr(LLMClient, "send", lambda self, **kw: next(calls))
    monkeypatch.setattr(
        "code_review_agent.tools.post_review_comment.httpx.post",
        lambda *a, **kw: SimpleNamespace(
            raise_for_status=lambda: None, json=lambda: {"id": 42}
        ),
    )
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/widgets")
    monkeypatch.setenv("GITHUB_PR_NUMBER", "1")

    result = run_agent("diff --git a/x b/x", make_config())

    assert result["ok"] is True
    assert result["steps"] == 3
    assert result["comments_posted"] == 1
    assert "no issues" in result["summary"].lower()


def test_max_steps_guardrail_triggers(monkeypatch):
    state = {"n": 0}

    def always_tool_use(self, **kw):
        n = state["n"]
        state["n"] += 1
        # distinct args each call so loop-detection doesn't fire first
        return fake_response(
            [tool_use_block("list_directory", {"path": f"dir{n}"}, f"t{n}")], "tool_use"
        )

    monkeypatch.setattr(LLMClient, "send", always_tool_use)

    with pytest.raises(GuardrailViolation) as exc_info:
        run_agent("diff", make_config(max_steps=3))
    assert exc_info.value.guardrail == "max_steps"


def test_max_input_tokens_guardrail_triggers(monkeypatch):
    def oversized_turn(self, **kw):
        return fake_response(
            [text_block("done")], "end_turn", input_tokens=250_000, output_tokens=1_000
        )

    monkeypatch.setattr(LLMClient, "send", oversized_turn)

    with pytest.raises(GuardrailViolation) as exc_info:
        run_agent("diff", make_config(max_input_tokens=200_000))
    assert exc_info.value.guardrail == "max_input_tokens"


def test_total_token_budget_guardrail_triggers(monkeypatch):
    state = {"n": 0}

    def growing_usage(self, **kw):
        n = state["n"]
        state["n"] += 1
        return fake_response(
            [tool_use_block("list_directory", {"path": f"d{n}"}, f"t{n}")],
            "tool_use",
            input_tokens=150_000,
            output_tokens=10_000,
        )

    monkeypatch.setattr(LLMClient, "send", growing_usage)

    with pytest.raises(GuardrailViolation) as exc_info:
        run_agent(
            "diff", make_config(max_steps=100, max_total_tokens=500_000, max_input_tokens=200_000)
        )
    assert exc_info.value.guardrail == "token_budget"


def test_loop_detection_guardrail_triggers(monkeypatch):
    def identical_call(self, **kw):
        return fake_response(
            [tool_use_block("grep_code", {"pattern": "TODO"}, "t")], "tool_use"
        )

    monkeypatch.setattr(LLMClient, "send", identical_call)

    with pytest.raises(GuardrailViolation) as exc_info:
        run_agent("diff", make_config(max_steps=100))
    assert exc_info.value.guardrail == "loop_detection"
