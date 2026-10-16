"""Minimal OpenAI-compatible Chat Completions client (tool calling).

Works with any provider that speaks ``POST {base}/chat/completions``:
OpenAI, OpenRouter, Groq, Together, a local Ollama or vLLM, and others.
No vendor SDK: one httpx call.
"""

import httpx


class LLMError(Exception):
    """Raised on any transport, HTTP, or response-shape failure."""


class LLMClient:
    """Chat Completions client.

    Args:
        base_url: API base, e.g. ``https://api.openai.com/v1``.
        api_key: Bearer key for the provider.
        model: Model name.
        client: httpx client used for the request.
        timeout: Per-request timeout in seconds.
    """

    def __init__(self, base_url: str, api_key: str, model: str,
                 client: httpx.Client, timeout: float = 30):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.api_key = api_key
        self.model = model
        self.client = client
        self.timeout = timeout

    def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        """Send one chat turn and return the assistant message.

        Args:
            messages: OpenAI-format message list.
            tools: OpenAI-format function tool specs.

        Returns:
            The ``choices[0].message`` dict (may carry ``tool_calls``).

        Raises:
            LLMError: On timeout, non-2xx status, or malformed JSON.

        Example:
            >>> msg = llm.chat([{"role": "user", "content": "hi"}], [])
            >>> msg["role"]
            'assistant'
        """
        try:
            r = self.client.post(
                self.url, timeout=self.timeout,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": messages, "tools": tools,
                      "tool_choice": "auto", "temperature": 0})
            r.raise_for_status()
            message = r.json()["choices"][0]["message"]
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as e:
            raise LLMError(f"{type(e).__name__}: {e}") from e
        if not isinstance(message, dict):
            raise LLMError("message is not an object")
        return message
