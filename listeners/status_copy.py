"""Trust-aligned assistant status text shown while TruthExpiry validates a claim."""

ASSISTANT_STATUS = "Validating claim against lifecycle evidence..."

ASSISTANT_LOADING_MESSAGES: tuple[str, ...] = (
    "Searching public Slack channels for evidence...",
    "Extracting structured claims from evidence...",
    "Fetching authoritative lifecycle records...",
    "Applying deterministic validity rules...",
)
