from listeners.views.app_home_builder import build_app_home_view
from listeners.views.feedback_builder import build_feedback_blocks


def test_build_feedback_blocks():
    blocks = build_feedback_blocks()

    assert len(blocks) > 0
    block_dict = blocks[0].to_dict()
    action_ids = [e["action_id"] for e in block_dict["elements"]]
    assert "feedback" in action_ids


def test_build_app_home_view_truth_expiry():
    view = build_app_home_view()

    assert view["type"] == "home"
    block_types = [b["type"] for b in view["blocks"]]
    assert "header" in block_types
    assert "section" in block_types

    section_texts = [
        b["text"]["text"] for b in view["blocks"] if b["type"] == "section"
    ]
    assert any("TruthExpiry" in text for text in section_texts)
    assert any("public channels" in text for text in section_texts)
    assert not any("Slack MCP Server" in text for text in section_texts)
