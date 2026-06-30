"""OpenAI-only claim extraction agent factory for Milestone 3."""

from __future__ import annotations

from pydantic_ai import Agent

from adapters.llm.contracts import ClaimExtractionOutputDto
from adapters.llm.prompt import SYSTEM_PROMPT

OPENAI_EXTRACTION_MODEL = "openai:gpt-4.1-mini"


def create_extraction_agent() -> Agent[None, ClaimExtractionOutputDto]:
    return Agent(
        OPENAI_EXTRACTION_MODEL,
        output_type=ClaimExtractionOutputDto,
        system_prompt=SYSTEM_PROMPT,
        tools=[],
    )
