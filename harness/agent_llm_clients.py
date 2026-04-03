"""Provider clients for Layer 2 tool-using agent turns."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from harness.agent_types import AgentTurnResult, ToolCallRequest
from harness.retry import HTTPRequestError, post_json_with_retry


class AgentLLMClientError(RuntimeError):
    """Raised when a Layer 2 provider call fails."""


@dataclass
class BaseAgentLLMClient:
    api_key: str

    def run_turn(
        self,
        *,
        model: str,
        system_prompt: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
        temperature: float,
        max_tokens: int,
    ) -> AgentTurnResult:
        raise NotImplementedError


class AnthropicAgentClient(BaseAgentLLMClient):
    endpoint = "https://api.anthropic.com/v1/messages"

    def run_turn(
        self,
        *,
        model: str,
        system_prompt: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
        temperature: float,
        max_tokens: int,
    ) -> AgentTurnResult:
        payload: dict[str, Any] = {
            "model": model,
            "system": system_prompt,
            "messages": _to_anthropic_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        anthropic_tools = _to_anthropic_tools(tools)
        if anthropic_tools:
            payload["tools"] = anthropic_tools

        raw_response, headers = _post_json(
            url=self.endpoint,
            payload=payload,
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            service_name="anthropic",
        )
        return _normalize_anthropic_response(raw_response, headers)


class OpenAIAgentClient(BaseAgentLLMClient):
    endpoint = "https://api.openai.com/v1/chat/completions"

    def run_turn(
        self,
        *,
        model: str,
        system_prompt: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
        temperature: float,
        max_tokens: int,
    ) -> AgentTurnResult:
        payload: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": _to_openai_messages(system_prompt=system_prompt, messages=messages),
        }
        if tools:
            payload["tools"] = tools

        raw_response, headers = _post_json(
            url=self.endpoint,
            payload=payload,
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {self.api_key}",
            },
            service_name="openai",
        )
        return _normalize_openai_response(raw_response, headers)


def create_agent_llm_client(provider: str, api_key: str | None) -> BaseAgentLLMClient:
    if not api_key:
        raise AgentLLMClientError(f"Missing API key for provider '{provider}'")
    normalized = provider.lower()
    if normalized == "anthropic":
        return AnthropicAgentClient(api_key=api_key)
    if normalized == "openai":
        return OpenAIAgentClient(api_key=api_key)
    raise AgentLLMClientError(f"Unsupported provider '{provider}'")


def _post_json(
    *,
    url: str,
    payload: dict[str, object],
    headers: dict[str, str],
    service_name: str,
) -> tuple[dict[str, object], dict[str, str]]:
    try:
        return post_json_with_retry(
            url=url,
            payload=payload,
            headers=headers,
            timeout_seconds=60,
            service_name=service_name,
            max_attempts=5,
            base_backoff_seconds=1.0,
            max_backoff_seconds=16.0,
        )
    except HTTPRequestError as exc:
        raise AgentLLMClientError(str(exc)) from exc


def _to_openai_messages(
    *,
    system_prompt: str,
    messages: list[dict[str, object]],
) -> list[dict[str, object]]:
    converted: list[dict[str, object]] = [{"role": "system", "content": system_prompt}]
    for message in messages:
        role = str(message.get("role", ""))
        if role == "user":
            converted.append({"role": "user", "content": _content_as_text(message.get("content"))})
            continue
        if role == "assistant":
            assistant_payload: dict[str, Any] = {
                "role": "assistant",
                "content": _content_as_text(message.get("content")),
            }
            tool_calls = message.get("tool_calls")
            if isinstance(tool_calls, list) and tool_calls:
                assistant_payload["tool_calls"] = [
                    {
                        "id": str(call.get("id", "")),
                        "type": "function",
                        "function": {
                            "name": str(call.get("name", "")),
                            "arguments": json.dumps(call.get("arguments", {}), ensure_ascii=False),
                        },
                    }
                    for call in tool_calls
                    if isinstance(call, dict)
                ]
            converted.append(assistant_payload)
            continue
        if role == "tool":
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": str(message.get("tool_call_id", "")),
                    "content": _content_as_text(message.get("content")),
                }
            )
            continue
    return converted


def _to_anthropic_messages(messages: list[dict[str, object]]) -> list[dict[str, object]]:
    converted: list[dict[str, object]] = []
    for message in messages:
        role = str(message.get("role", ""))
        if role == "user":
            converted.append({"role": "user", "content": _content_as_text(message.get("content"))})
            continue

        if role == "assistant":
            blocks: list[dict[str, Any]] = []
            text = _content_as_text(message.get("content"))
            if text:
                blocks.append({"type": "text", "text": text})
            tool_calls = message.get("tool_calls")
            if isinstance(tool_calls, list):
                for call in tool_calls:
                    if not isinstance(call, dict):
                        continue
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": str(call.get("id", "")),
                            "name": str(call.get("name", "")),
                            "input": call.get("arguments", {}),
                        }
                    )
            converted.append({"role": "assistant", "content": blocks if blocks else text})
            continue

        if role == "tool":
            converted.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": str(message.get("tool_call_id", "")),
                            "content": _content_as_text(message.get("content")),
                        }
                    ],
                }
            )
            continue

    return converted


def _to_anthropic_tools(tools: list[dict[str, object]]) -> list[dict[str, object]]:
    converted: list[dict[str, object]] = []
    for tool in tools:
        function_payload = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(function_payload, dict):
            continue
        name = function_payload.get("name")
        description = function_payload.get("description")
        parameters = function_payload.get("parameters")
        if not isinstance(name, str) or not isinstance(parameters, dict):
            continue
        converted.append(
            {
                "name": name,
                "description": description if isinstance(description, str) else "",
                "input_schema": parameters,
            }
        )
    return converted


def _normalize_openai_response(
    raw_response: dict[str, object],
    headers: dict[str, str],
) -> AgentTurnResult:
    choices = raw_response.get("choices")
    choice = choices[0] if isinstance(choices, list) and choices else {}
    if not isinstance(choice, dict):
        choice = {}

    message = choice.get("message")
    if not isinstance(message, dict):
        message = {}

    content = message.get("content")
    if isinstance(content, list):
        text = "\n".join(
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ).strip()
    else:
        text = str(content or "").strip()

    tool_calls = _extract_openai_tool_calls(message.get("tool_calls"))
    finish_reason = choice.get("finish_reason")
    stop_reason = _normalize_openai_finish_reason(finish_reason, has_tool_calls=bool(tool_calls))

    usage = raw_response.get("usage")
    usage_obj = usage if isinstance(usage, dict) else {}

    request_id = _extract_request_id(headers)
    return AgentTurnResult(
        text=text,
        tool_calls=tool_calls,
        stop_reason=stop_reason,
        request_id=request_id,
        tokens_in=_coerce_optional_int(usage_obj.get("prompt_tokens")),
        tokens_out=_coerce_optional_int(usage_obj.get("completion_tokens")),
        raw_response=raw_response,
    )


def _normalize_anthropic_response(
    raw_response: dict[str, object],
    headers: dict[str, str],
) -> AgentTurnResult:
    content = raw_response.get("content")
    blocks = content if isinstance(content, list) else []

    text_parts: list[str] = []
    tool_calls: list[ToolCallRequest] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type == "text":
            value = block.get("text")
            if isinstance(value, str) and value.strip():
                text_parts.append(value.strip())
        elif block_type == "tool_use":
            tool_calls.append(
                ToolCallRequest(
                    id=str(block.get("id", "")),
                    name=str(block.get("name", "")),
                    arguments=block.get("input", {}) if isinstance(block.get("input"), dict) else {},
                )
            )

    stop_reason = _normalize_anthropic_stop_reason(raw_response.get("stop_reason"), bool(tool_calls))
    usage = raw_response.get("usage")
    usage_obj = usage if isinstance(usage, dict) else {}

    request_id = _extract_request_id(headers)
    return AgentTurnResult(
        text="\n".join(text_parts).strip(),
        tool_calls=tool_calls,
        stop_reason=stop_reason,
        request_id=request_id,
        tokens_in=_coerce_optional_int(usage_obj.get("input_tokens")),
        tokens_out=_coerce_optional_int(usage_obj.get("output_tokens")),
        raw_response=raw_response,
    )


def _extract_openai_tool_calls(payload: Any) -> list[ToolCallRequest]:
    if not isinstance(payload, list):
        return []
    calls: list[ToolCallRequest] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        function = item.get("function")
        if not isinstance(function, dict):
            continue
        arguments_raw = function.get("arguments")
        arguments = _parse_json_object(arguments_raw)
        calls.append(
            ToolCallRequest(
                id=str(item.get("id", "")),
                name=str(function.get("name", "")),
                arguments=arguments,
            )
        )
    return calls


def _parse_json_object(value: Any) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items()}
    if not isinstance(value, str):
        return {}
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if isinstance(decoded, dict):
        return {str(k): v for k, v in decoded.items()}
    return {}


def _normalize_openai_finish_reason(value: Any, has_tool_calls: bool) -> str:
    if value == "tool_calls" or has_tool_calls:
        return "tool_calls"
    if value == "stop":
        return "completed"
    if value == "length":
        return "max_tokens_truncated"
    return "unexpected"


def _normalize_anthropic_stop_reason(value: Any, has_tool_calls: bool) -> str:
    if value == "tool_use" or has_tool_calls:
        return "tool_calls"
    if value == "end_turn":
        return "completed"
    if value == "max_tokens":
        return "max_tokens_truncated"
    return "unexpected"


def _extract_request_id(headers: dict[str, str]) -> str | None:
    for key in ("request-id", "x-request-id"):
        value = headers.get(key)
        if value:
            return value
    return None


def _content_as_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                chunks.append(str(item["text"]))
        return "\n".join(chunk for chunk in chunks if chunk).strip()
    return ""


def _coerce_optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None
