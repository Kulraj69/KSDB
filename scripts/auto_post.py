#!/usr/bin/env python3
"""
Webhook-based auto-poster.

Usage:
  python scripts/auto_post.py --dry-run
  python scripts/auto_post.py

Env vars:
  AUTOPOST_WEBHOOK_URL  Required for real posting.
  AUTOPOST_TIMEZONE     Optional IANA timezone (default: Asia/Kolkata).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent.parent
SCHEDULE_PATH = ROOT / "automation" / "monthly_posts.json"
STATE_PATH = ROOT / "automation" / ".autopost_state.json"


@dataclass
class ScheduledPost:
    id: str
    publish_at: datetime
    title: str
    body: str
    ready: bool


def load_schedule(timezone_name: str) -> list[ScheduledPost]:
    tz = ZoneInfo(timezone_name)
    data = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
    posts: list[ScheduledPost] = []
    for item in data:
        local_dt = datetime.fromisoformat(item["publish_at"]).replace(tzinfo=tz)
        posts.append(
            ScheduledPost(
                id=item["id"],
                publish_at=local_dt,
                title=item["title"],
                body=item["body"],
                ready=bool(item.get("ready", True)),
            )
        )
    return posts


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"posted_ids": []}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"posted_ids": []}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def post_to_webhook(webhook_url: str, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        webhook_url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=15) as response:
        status = response.getcode()
        if status < 200 or status >= 300:
            raise RuntimeError(f"Webhook returned non-2xx status: {status}")


def run(dry_run: bool) -> int:
    timezone_name = os.getenv("AUTOPOST_TIMEZONE", "Asia/Kolkata")
    now = datetime.now(ZoneInfo(timezone_name))
    webhook_url = os.getenv("AUTOPOST_WEBHOOK_URL", "").strip()
    schedule = load_schedule(timezone_name)
    state = load_state()
    posted_ids = set(state.get("posted_ids", []))
    changed = False

    due_posts = [
        post
        for post in schedule
        if now >= post.publish_at and post.id not in posted_ids and post.ready
    ]
    pending_slots = [
        post
        for post in schedule
        if now >= post.publish_at and post.id not in posted_ids and not post.ready
    ]
    if not due_posts:
        if pending_slots:
            print(
                f"No ready posts to publish. {len(pending_slots)} due slot(s) are waiting for story content."
            )
            return 0
        print("No due posts at this time.")
        return 0

    for post in due_posts:
        payload = {
            "id": post.id,
            "title": post.title,
            "body": post.body,
            "publish_at": post.publish_at.isoformat(),
            "posted_at": now.isoformat(),
        }

        if dry_run:
            print(f"[DRY RUN] Would post: {post.id} at {post.publish_at.isoformat()}")
            continue

        if not webhook_url:
            print(
                "AUTOPOST_WEBHOOK_URL is not set. Set it first to enable posting.",
                file=sys.stderr,
            )
            return 1

        try:
            post_to_webhook(webhook_url, payload)
            posted_ids.add(post.id)
            changed = True
            print(f"Posted: {post.id}")
        except (HTTPError, URLError, RuntimeError) as exc:
            print(f"Failed to post {post.id}: {exc}", file=sys.stderr)
            return 1

    if changed:
        state["posted_ids"] = sorted(posted_ids)
        save_state(state)

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run monthly webhook auto-poster")
    parser.add_argument("--dry-run", action="store_true", help="Print due posts without sending")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(run(dry_run=args.dry_run))
