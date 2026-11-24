"""Posts one chapter announcement to #beta-updates in the Beta System's voice.

Run by the "Announce a chapter" GitHub workflow, which fills these in from its form:
  CHAPTER_TITLE, CHAPTER_LINK, SYSTEM_LINE (optional)
and from repository secrets:
  DISCORD_WEBHOOK_URL, READER_ROLE_ID (optional), BOT_AVATAR_URL (optional)
"""

from __future__ import annotations

import asyncio
import os
import sys

import aiohttp

import voice
from notifier import EMBED_COLOR, post
from webnovel import Chapter


async def main() -> int:
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    title = os.getenv("CHAPTER_TITLE", "").strip()
    link = os.getenv("CHAPTER_LINK", "").strip()
    line = os.getenv("SYSTEM_LINE", "").strip() or voice.new_chapter_line()
    role_id = os.getenv("READER_ROLE_ID", "").strip()

    if not webhook:
        print("Missing the DISCORD_WEBHOOK_URL secret.")
        return 1
    if not title or not link.startswith("https://"):
        print("Please give a chapter title and a full https:// link.")
        return 1

    chapter = Chapter(id="manual", title=title)
    embed = {
        "author": {"name": voice.header()},
        "title": chapter.title[:256],
        "url": link,
        "description": f"{voice.glitch(line)}\n\n**[▶ Read it on WebNovel]({link})**",
        "color": EMBED_COLOR,
        "footer": {"text": voice.footer()},
    }
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        await post(session, webhook, {
            "content": voice.ping_text(f"<@&{role_id}>") if role_id else None,
            "embeds": [embed],
            "allowed_mentions": {"parse": [], "roles": [role_id] if role_id else []},
        })
    print(f"Announced: {title}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
