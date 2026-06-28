from logging import Logger

from slack_bolt.context.set_suggested_prompts import SetSuggestedPrompts

SUGGESTED_PROMPTS = [
    {
        "title": "Check report export",
        "message": "Is report export available on the starter plan?",
    },
    {
        "title": "Verify rate limits",
        "message": "What is the API rate limit for starter workspaces?",
    },
    {
        "title": "Refund policy",
        "message": "What is the current enterprise refund policy?",
    },
]


def handle_assistant_thread_started(
    set_suggested_prompts: SetSuggestedPrompts, logger: Logger
):
    """Set TruthExpiry suggested prompts when a user opens the assistant panel."""
    try:
        set_suggested_prompts(
            prompts=SUGGESTED_PROMPTS,
            title="Which claim should TruthExpiry verify?",
        )
    except Exception as e:
        logger.exception(f"Failed to handle assistant_thread_started: {e}")
