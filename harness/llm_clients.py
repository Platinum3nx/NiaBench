"""Minimal provider clients for evaluation and judge calls."""

from __future__ import annotations

from dataclasses import dataclass

from harness.retry import HTTPRequestError, post_json_with_retry
from harness.types import ModelResponse


class LLMClientError(RuntimeError):
    """Raised when a model provider call fails."""


@dataclass
class BaseLLMClient:
    api_key: str

    def generate(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0,
        max_tokens: int = 2048,
    ) -> ModelResponse:
        raise NotImplementedError


class AnthropicClient(BaseLLMClient):
    endpoint = "https://api.anthropic.com/v1/messages"

    def generate(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0,
        max_tokens: int = 2048,
    ) -> ModelResponse:
        payload = {
            "model": model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        raw_response, headers = _post_json(
            self.endpoint,
            payload,
            {
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            service_name="anthropic",
        )
        text_parts = [
            block.get("text", "")
            for block in raw_response.get("content", [])
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        usage = raw_response.get("usage", {})
        return ModelResponse(
            text="\n".join(part for part in text_parts if part).strip(),
            tokens_in=usage.get("input_tokens"),
            tokens_out=usage.get("output_tokens"),
            raw_response=raw_response,
            request_id=headers.get("request-id"),
        )


class OpenAIClient(BaseLLMClient):
    endpoint = "https://api.openai.com/v1/chat/completions"

    def generate(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0,
        max_tokens: int = 2048,
    ) -> ModelResponse:
        payload = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        raw_response, headers = _post_json(
            self.endpoint,
            payload,
            {
                "content-type": "application/json",
                "authorization": f"Bearer {self.api_key}",
            },
            service_name="openai",
        )
        choice = raw_response.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            text = "\n".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ).strip()
        else:
            text = str(content).strip()
        usage = raw_response.get("usage", {})
        return ModelResponse(
            text=text,
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            raw_response=raw_response,
            request_id=headers.get("x-request-id"),
        )


def create_llm_client(provider: str, api_key: str | None) -> BaseLLMClient:
    if not api_key:
        raise LLMClientError(f"Missing API key for provider '{provider}'")
    normalized = provider.lower()
    if normalized == "anthropic":
        return AnthropicClient(api_key)
    if normalized == "openai":
        return OpenAIClient(api_key)
    raise LLMClientError(f"Unsupported provider '{provider}'")


def _post_json(
    url: str,
    payload: dict[str, object],
    headers: dict[str, str],
    *,
    service_name: str,
) -> tuple[dict[str, object], dict[str, str]]:
    try:
        response, response_headers = post_json_with_retry(
            url=url,
            payload=payload,
            headers=headers,
            timeout_seconds=60,
            service_name=service_name,
            max_attempts=5,
            base_backoff_seconds=1.0,
            max_backoff_seconds=16.0,
        )
        return response, response_headers
    except HTTPRequestError as exc:
        raise LLMClientError(str(exc)) from exc
