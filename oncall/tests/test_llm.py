"""Unit tests for the OpenAI-compatible chat client against a fake server."""

import json

import httpx
import pytest

from oncall.llm import LLMClient, LLMError


def make(handler):
    return LLMClient("http://llm/v1/", "test-key", "test-model",
                     httpx.Client(transport=httpx.MockTransport(handler)))


def test_chat_sends_openai_request_and_returns_message():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {
            "role": "assistant", "content": "hi"}}]})

    msg = make(handler).chat([{"role": "user", "content": "x"}], [{"type": "function"}])
    assert msg == {"role": "assistant", "content": "hi"}
    assert seen["url"] == "http://llm/v1/chat/completions"
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["tools"] == [{"type": "function"}]


@pytest.mark.parametrize("response", [
    httpx.Response(500, json={"error": "x"}),
    httpx.Response(200, json={"choices": []}),
    httpx.Response(200, text="not json"),
])
def test_chat_bad_responses_raise(response):
    with pytest.raises(LLMError):
        make(lambda request: response).chat([], [])


def test_chat_timeout_raises():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(LLMError):
        make(handler).chat([], [])
