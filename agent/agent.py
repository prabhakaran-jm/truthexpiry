import logging
import os

from pydantic_ai import Agent

from agent.deps import AgentDeps

SYSTEM_PROMPT = """\
You are TruthExpiry's optional claim-extraction assistant.

Extract structured claims from user questions. Do not assign validity labels.
TruthExpiry's deterministic labeler assigns CURRENT, SUPERSEDED, CONFLICTING,
or UNVERIFIED based on lifecycle evidence.
"""

logger = logging.getLogger(__name__)

_cached_model: str | None = None


def get_model() -> str:
    """Select the AI model when live LLM extraction is enabled (post-Milestone 0)."""
    global _cached_model
    if _cached_model is not None:
        return _cached_model

    if os.environ.get("ANTHROPIC_API_KEY"):
        _cached_model = "anthropic:claude-sonnet-4-6"
    elif os.environ.get("OPENAI_API_KEY"):
        _cached_model = "openai:gpt-4.1-mini"
    else:
        raise RuntimeError(
            "No AI provider configured. "
            "Set ANTHROPIC_API_KEY or OPENAI_API_KEY in your environment."
        )
    return _cached_model


agent = Agent(
    deps_type=AgentDeps,
    system_prompt=SYSTEM_PROMPT,
    tools=[],
)


def run_agent(text, deps, message_history=None):
    """Deferred scaffold entrypoint; M3 extraction uses agent.extraction_agent."""
    del text, deps, message_history
    raise NotImplementedError(
        "Use TRUTH_EXPIRY_CLAIM_EXTRACTOR=live with the M3 extraction adapter, "
        "or TRUTH_EXPIRY_USE_FAKES=1 with FakeClaimExtractionPort."
    )
