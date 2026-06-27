from dataclasses import dataclass, field


@dataclass
class FakeSlackRenderer:
    """Records Slack UI actions without calling the Web API."""

    status_updates: list[str] = field(default_factory=list)
    streamed_markdown: list[str] = field(default_factory=list)
    posted_messages: list[str] = field(default_factory=list)

    def set_status(self, status: str) -> None:
        self.status_updates.append(status)

    def stream_markdown(self, markdown_text: str) -> None:
        self.streamed_markdown.append(markdown_text)

    def post_message(self, text: str) -> None:
        self.posted_messages.append(text)
