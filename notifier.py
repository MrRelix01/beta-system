"""Beta System chapter notifier: the GitHub Actions version.

GitHub runs this every 15 minutes. It checks WebNovel once, posts any new chapters to
#beta-updates through a Discord webhook, saves what it has seen in state.json, and exits.
No server or always-on PC needed.

Settings come from GitHub repository secrets (see README):
  DISCORD_WEBHOOK_URL   webhook for #beta-updates                (required)
  WEBNOVEL_BOOK         Beta System book link or ID              (required)
  READER_ROLE_ID        role to ping (Beta System Reader)        (optional)
  MOD_WEBHOOK_URL       webhook for #mod-logs, for error reports (optional)
  BOT_AVATAR_URL        image link for the webhook's avatar      (optional)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

import voice
from webnovel import Chapter, FetchError, book_id_from, chapter_url, fetch_chapters

HERE = Path(__file__).resolve().parent
STATE_FILE = HERE / "state.json"
EMBED_COLOR = 0x4FA3D9
BOT_NAME = "Beta System"
MAX_SINGLE_POSTS = 3
KEEPALIVE_DAYS = 45  # GitHub pauses timers in repos with no activity for 60 days


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"seen_ids": [], "latest": None, "failures": 0, "keepalive": None}


def save_state(state: dict) -> None:
    state["seen_ids"] = state["seen_ids"][-2000:]
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def chapter_embed(chapter: Chapter, book_id: str, line: str) -> dict:
    url = chapter.url or chapter_url(book_id, chapter.id)
    embed = {
        "author": {"name": voice.header()},
        "title": chapter.title[:256],
        "url": url,
        "description": f"{voice.glitch(line)}\n\n**[▶ Read it on WebNovel]({url})**",
        "color": EMBED_COLOR,
        "footer": {"text": voice.footer()},
    }
    if chapter.locked:
        embed["fields"] = [{"name": "Access", "value": "🔒 Locked / paid chapter", "inline": True}]
    return embed


async def post(session: aiohttp.ClientSession, webhook: str, payload: dict) -> None:
    payload.setdefault("username", BOT_NAME)
    avatar = os.getenv("BOT_AVATAR_URL", "").strip()
    if avatar:
        payload.setdefault("avatar_url", avatar)
    async with session.post(webhook, params={"wait": "true"}, json=payload) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"Discord webhook returned {resp.status}: {await resp.text()}")


async def announce(session, webhook: str, role_id: str, book_id: str, chapters: list[Chapter]) -> None:
    ping = voice.ping_text(f"<@&{role_id}>") if role_id else None
    mentions = {"parse": [], "roles": [role_id] if role_id else []}
    if len(chapters) <= MAX_SINGLE_POSTS:
        for chapter in chapters:
            await post(session, webhook, {
                "content": ping,
                "embeds": [chapter_embed(chapter, book_id, voice.new_chapter_line())],
                "allowed_mentions": mentions,
            })
    else:
        listing = "\n".join(
            f"• [{c.title}]({c.url or chapter_url(book_id, c.id)})" for c in chapters[-15:]
        )
        await post(session, webhook, {
            "content": ping,
            "embeds": [{
                "author": {"name": voice.header()},
                "title": f"{len(chapters)} new chapters",
                "description": f"{voice.glitch(voice.multi_chapter_line(len(chapters)))}\n\n{listing}",
                "color": EMBED_COLOR,
                "footer": {"text": voice.footer()},
            }],
            "allowed_mentions": mentions,
        })


async def notify_mods(session, text: str) -> None:
    webhook = os.getenv("MOD_WEBHOOK_URL", "").strip()
    if not webhook:
        return
    try:
        await post(session, webhook, {
            "content": f"**[Beta System // diagnostics]** {text}",
            "allowed_mentions": {"parse": []},
        })
    except RuntimeError as exc:
        print(f"Couldn't post to mod webhook: {exc}")


async def main() -> int:
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    book = os.getenv("WEBNOVEL_BOOK", "").strip()
    role_id = os.getenv("READER_ROLE_ID", "").strip()
    if not webhook or not book:
        print("Missing DISCORD_WEBHOOK_URL or WEBNOVEL_BOOK secret.")
        return 1
    book_id = book_id_from(book)
    state = load_state()

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        try:
            chapters = await fetch_chapters(session, book_id)
        except FetchError as exc:
            state["failures"] = state.get("failures", 0) + 1
            state["last_error"] = f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC: {exc}"[:1500]
            print(f"Fetch failed ({state['failures']} in a row): {exc}")
            if state["failures"] in (3, 12, 48, 192):
                await notify_mods(session, f"{voice.fetch_failure_line(state['failures'])}\n`{exc}`")
            save_state(state)
            return 0  # not a crash; try again next run

        if state.get("failures", 0) >= 3:
            await notify_mods(session, "Connection restored. I'd like to say I fixed it. I didn't.")
        state["failures"] = 0
        state.pop("last_error", None)

        seen = set(state["seen_ids"])
        if not seen:
            state["seen_ids"] = [c.id for c in chapters]
            print(f"Baseline saved: {len(chapters)} existing chapters. Nothing announced.")
            await notify_mods(
                session,
                f"Calibration complete. {len(chapters)} existing chapters logged. "
                "I'll only announce chapters published from now on.",
            )
        else:
            new = [c for c in chapters if c.id not in seen]
            if new:
                await announce(session, webhook, role_id, book_id, new)
                state["seen_ids"].extend(c.id for c in new)
                print(f"Announced {len(new)} chapter(s): {[c.title for c in new]}")
            else:
                print(f"No new chapters ({len(chapters)} total).")

        if chapters:
            state["latest"] = chapters[-1].to_dict()

    # Touch the state now and then so GitHub sees repo activity and keeps the timer on.
    last = state.get("keepalive")
    if not last or time.time() - last > KEEPALIVE_DAYS * 86400:
        state["keepalive"] = int(time.time())
        print(f"Keepalive refreshed {datetime.now(timezone.utc):%Y-%m-%d}.")

    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
