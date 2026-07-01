#!/usr/bin/env python3
"""Post synthetic public-channel evidence for the TruthExpiry demo workspace."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from truthexpiry.services.demo_guidance import DEMO_SEED_MESSAGES  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Post demo evidence messages to a public Slack channel so "
            "assistant.search.context can retrieve them for judges."
        ),
    )
    parser.add_argument(
        "--channel",
        required=True,
        help="Public channel ID (starts with C) where the bot is already a member.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=1.0,
        help="Pause between posts to avoid rate limits (default: 1.0).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print messages without calling Slack.",
    )
    return parser


def _validate_channel_id(channel: str) -> str:
    channel_id = channel.strip()
    if not channel_id.startswith("C"):
        raise ValueError("channel must be a public channel ID starting with C")
    return channel_id


def seed_channel(
    *,
    client,
    channel_id: str,
    messages: tuple[str, ...] = DEMO_SEED_MESSAGES,
    delay_seconds: float = 1.0,
    dry_run: bool = False,
) -> list[str]:
    """Post seed messages; returns posted message timestamps."""
    channel_id = _validate_channel_id(channel_id)
    timestamps: list[str] = []
    for index, text in enumerate(messages):
        if dry_run:
            print(f"[dry-run] #{index + 1}: {text}")
            timestamps.append(f"dry-run-{index}")
            continue
        response = client.chat_postMessage(channel=channel_id, text=text)
        timestamps.append(str(response["ts"]))
        if index + 1 < len(messages) and delay_seconds > 0:
            time.sleep(delay_seconds)
    return timestamps


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        channel_id = _validate_channel_id(args.channel)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.delay_seconds < 0:
        parser.error("--delay-seconds must be zero or greater")

    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if not token and not args.dry_run:
        print(
            "SLACK_BOT_TOKEN is required (set in environment or .env).",
            file=sys.stderr,
        )
        return 1

    client = None
    if not args.dry_run:
        from slack_sdk import WebClient

        client = WebClient(token=token)

    try:
        timestamps = seed_channel(
            client=client,
            channel_id=channel_id,
            delay_seconds=args.delay_seconds,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"Failed to post seed messages: {exc.__class__.__name__}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(f"Would post {len(timestamps)} messages to {channel_id}.")
    else:
        print(f"Posted {len(timestamps)} messages to {channel_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
