"""Condition registry for Layer 2 agent benchmark runs."""

from __future__ import annotations

from dataclasses import dataclass

from harness.agent_types import AgentCondition


@dataclass(frozen=True)
class AgentConditionConfig:
    id: AgentCondition
    description: str
    include_nia_tool: bool


NO_RETRIEVAL_AGENT = AgentConditionConfig(
    id="no_retrieval_agent",
    description="Local workspace tools only; no external retrieval tools.",
    include_nia_tool=False,
)

NIA_AGENT = AgentConditionConfig(
    id="nia_agent",
    description="Identical local tools plus one structured Nia documentation retrieval tool.",
    include_nia_tool=True,
)

CONDITION_REGISTRY: dict[str, AgentConditionConfig] = {
    NO_RETRIEVAL_AGENT.id: NO_RETRIEVAL_AGENT,
    NIA_AGENT.id: NIA_AGENT,
}


def resolve_conditions(value: str) -> list[AgentConditionConfig]:
    normalized = value.strip().lower()
    if normalized == "all":
        return [NO_RETRIEVAL_AGENT, NIA_AGENT]
    config = CONDITION_REGISTRY.get(normalized)
    if config is None:
        expected = ", ".join(sorted((*CONDITION_REGISTRY.keys(), "all")))
        raise ValueError(f"Unsupported condition '{value}'. Expected one of: {expected}")
    return [config]
