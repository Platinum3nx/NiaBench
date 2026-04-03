#!/usr/bin/env python3
"""Smoke checks for Layer 2 agent client normalization."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.agent_llm_clients import (  # noqa: E402
    _normalize_anthropic_response,
    _normalize_openai_response,
)


def main() -> int:
    openai_raw = {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {"name": "read_file", "arguments": "{\"path\":\"a.txt\"}"},
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7},
    }
    openai_turn = _normalize_openai_response(openai_raw, {"x-request-id": "req_openai"})
    assert openai_turn.stop_reason == "tool_calls"
    assert len(openai_turn.tool_calls) == 1
    assert openai_turn.tool_calls[0].name == "read_file"

    anthropic_raw = {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": "completed"}],
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }
    anthropic_turn = _normalize_anthropic_response(anthropic_raw, {"request-id": "req_anthropic"})
    assert anthropic_turn.stop_reason == "completed"
    assert anthropic_turn.text == "completed"

    print("Layer 2 client normalization smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
