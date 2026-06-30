from pathlib import Path

import listeners.events.app_mentioned as app_mentioned
import listeners.events.message as message_event
import listeners.truthexpiry_handler as truthexpiry_handler
from truthexpiry.ports.rts import EphemeralRtsHit, EphemeralRtsHits, RtsHitRef
from truthexpiry.services.rts_sanitizer import sanitize_rts_hits


def test_thread_context_package_removed():
    assert not Path("thread_context").exists()


def test_listeners_do_not_import_conversation_store():
    for module in (message_event, app_mentioned, truthexpiry_handler):
        source_path = Path(module.__file__).resolve()
        source = source_path.read_text(encoding="utf-8")
        assert "conversation_store" not in source
        assert "thread_context" not in source


def test_rts_hit_ref_has_no_message_body_field():
    fields = {field.name for field in RtsHitRef.__dataclass_fields__.values()}
    assert "message_text" not in fields
    assert "text" not in fields
    assert "body" not in fields
    assert "content" not in fields


def test_ephemeral_rts_hit_excludes_content_from_repr():
    hit = EphemeralRtsHit(
        team_id="T000",
        channel_id="C000",
        channel_name="demo",
        message_ts="1.0",
        permalink="https://example.invalid/p/1",
        content="secret message body",
    )
    rendered = repr(hit)
    assert "secret message body" not in rendered


def test_sanitizer_output_is_metadata_only():
    hits = EphemeralRtsHits(
        hits=(
            EphemeralRtsHit(
                team_id="T000",
                channel_id="C000",
                channel_name="demo",
                message_ts="1.0",
                permalink="https://example.invalid/p/1",
                content="Tracked in PROD-482.",
            ),
        )
    )
    refs = sanitize_rts_hits(hits)
    for ref in refs:
        assert ref.ref_type in {"slack_permalink", "ticket_id"}
        payload = ref.__dict__
        assert "message_text" not in payload
        assert "text" not in payload


def test_live_extractor_does_not_log_sensitive_values(caplog):
    import logging

    from adapters.llm.adapter import PydanticAiClaimExtractionAdapter
    from tests.fakes.extraction_runner import FakeExtractionRunner, make_claim_output

    secret_query = "secret-live-query"
    secret_body = "secret-live-body"
    hits = EphemeralRtsHits(
        hits=(
            EphemeralRtsHit(
                team_id="T000",
                channel_id="C000",
                channel_name="demo",
                message_ts="1.0",
                permalink="https://example.invalid/p/secret",
                content=secret_body,
            ),
        )
    )
    runner = FakeExtractionRunner(output=make_claim_output())
    adapter = PydanticAiClaimExtractionAdapter(runner=runner)
    with caplog.at_level(logging.DEBUG):
        adapter.extract_claims(secret_query, hits)
    assert secret_query not in caplog.text
    assert secret_body not in caplog.text
    assert "https://example.invalid/p/secret" not in caplog.text
