from logging import Logger

from slack_bolt.context.set_suggested_prompts import SetSuggestedPrompts

from truthexpiry.services.demo_guidance import suggested_prompt_payloads

SUGGESTED_PROMPTS_TITLE = "Which claim should TruthExpiry verify?"


def handle_assistant_thread_started(
    set_suggested_prompts: SetSuggestedPrompts, logger: Logger
):
    """Set TruthExpiry suggested prompts when a user opens the assistant panel."""
    try:
        set_suggested_prompts(
            prompts=suggested_prompt_payloads(),
            title=SUGGESTED_PROMPTS_TITLE,
        )
    except Exception:
        logger.exception("Failed to handle assistant_thread_started")
