def build_app_home_view() -> dict:
    """Build the TruthExpiry App Home view."""

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "TruthExpiry",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "TruthExpiry checks whether Slack answers are still *current* using "
                    "public-channel evidence and authoritative lifecycle records.\n\n"
                    "Send a *direct message* or *@mention* TruthExpiry in a public channel "
                    "to validate a claim."
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*MVP scope:* public channels only. Private search and OAuth are "
                    "not enabled in this milestone."
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "Statuses are assigned by deterministic rules — not by the LLM."
                    ),
                }
            ],
        },
    ]

    return {
        "type": "home",
        "blocks": blocks,
    }
