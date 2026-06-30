class SlackRtsResponseError(Exception):
    """Invalid or unsupported Slack RTS response."""


class SlackRtsTransportError(Exception):
    """Slack RTS transport or API failure."""
