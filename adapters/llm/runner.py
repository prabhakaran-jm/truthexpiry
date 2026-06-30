from __future__ import annotations

import logging
import time
from typing import Protocol

from pydantic_ai.exceptions import (
    AgentRunError,
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
)
from pydantic_ai.settings import ModelSettings

from adapters.llm.contracts import ClaimExtractionOutputDto
from adapters.llm.errors import (
    MalformedStructuredOutputError,
    ProviderTimeoutError,
    ProviderTransportError,
)
from agent.extraction_agent import create_extraction_agent

logger = logging.getLogger(__name__)

# Verified against pydantic-ai==1.107.0:
# Agent.run_sync(user_prompt=..., model_settings=ModelSettings(timeout=...))
# returns AgentRunResult with validated output on .output when output_type is set.
PROVIDER_TIMEOUT_SECONDS = 20


class ExtractionAgentRunner(Protocol):
    def run(
        self, *, system_prompt: str, user_prompt: str
    ) -> ClaimExtractionOutputDto: ...


class PydanticAiExtractionRunner:
    """OpenAI-backed synchronous extraction runner with a fixed timeout."""

    def __init__(self) -> None:
        self._agent = create_extraction_agent()
        self.last_call_count = 0

    def run(self, *, system_prompt: str, user_prompt: str) -> ClaimExtractionOutputDto:
        self.last_call_count += 1
        started = time.perf_counter()
        try:
            result = self._agent.run_sync(
                user_prompt,
                model_settings=ModelSettings(timeout=PROVIDER_TIMEOUT_SECONDS),
            )
        except TimeoutError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.warning(
                "Claim extraction provider failure outcome=timeout duration_ms=%s",
                duration_ms,
            )
            raise ProviderTimeoutError("Provider timeout") from exc
        except (ModelHTTPError, ModelAPIError, AgentRunError) as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.warning(
                "Claim extraction provider failure outcome=transport duration_ms=%s",
                duration_ms,
            )
            raise ProviderTransportError("Provider transport failure") from exc
        except UnexpectedModelBehavior as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.warning(
                "Claim extraction provider failure outcome=validation duration_ms=%s",
                duration_ms,
            )
            raise MalformedStructuredOutputError("Malformed structured output") from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        output = result.output
        if not isinstance(output, ClaimExtractionOutputDto):
            logger.warning(
                "Claim extraction provider failure outcome=validation duration_ms=%s",
                duration_ms,
            )
            raise MalformedStructuredOutputError("Unexpected output type")
        logger.info(
            "Claim extraction provider completed outcome=success duration_ms=%s claim_count=%s",
            duration_ms,
            0 if output.claim is None else 1,
        )
        return output
