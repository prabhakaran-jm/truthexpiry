from pathlib import Path

import listeners.events.app_mentioned as app_mentioned
import listeners.events.message as message_event
import listeners.truthexpiry_handler as truthexpiry_handler
from truthexpiry.ports.rts import EphemeralRtsHits, RtsHitRef
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


def test_sanitizer_output_is_metadata_only():
    hits = EphemeralRtsHits(
        hits=(
            RtsHitRef(
                channel_id="C000",
                message_ts="1.0",
                permalink="https://example.invalid/p/1",
            ),
        )
    )
    refs = sanitize_rts_hits(hits)
    for ref in refs:
        assert ref.ref_type in {"slack_permalink", "ticket_id"}
        payload = ref.__dict__
        assert "message_text" not in payload
        assert "text" not in payload
