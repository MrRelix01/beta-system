"""Fetches the chapter list for a WebNovel book.

WebNovel has no official public API, so this tries two approaches:
  1. The JSON endpoint the WebNovel website itself uses for its table of contents.
  2. Fallback: reading chapter links straight out of the book's catalog page HTML.

If WebNovel changes its site, this is the only file that should need fixing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

BASE = "https://www.webnovel.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class Chapter:
    id: str
    title: str
    index: int | None = None  # chapter number, when WebNovel provides it
    locked: bool = False  # True for paid/privilege chapters, when WebNovel says so
    book_id_hint: str = ""

    @property
    def url(self) -> str:
        return chapter_url(self.book_id_hint, self.id) if self.book_id_hint else ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def book_id_from(value: str) -> str:
    """Accepts a full WebNovel book URL or a bare numeric ID and returns the ID."""
    value = value.strip()
    if value.isdigit():
        return value
    match = re.search(r"/book/(?:[^/?#]*_)?(\d{6,})", value)
    if not match:
        raise ValueError(
            "Couldn't find a book ID in WEBNOVEL_BOOK. Paste the full book page link, "
            "e.g. https://www.webnovel.com/book/beta-system_12345678901234567"
        )
    return match.group(1)


def chapter_url(book_id: str, chapter_id: str) -> str:
    return f"{BASE}/book/{book_id}/{chapter_id}"


# ---------------------------------------------------------------- parsing (pure, testable)


def parse_chapter_json(data: Any, book_id: str) -> list[Chapter]:
    """Walks the JSON response and collects anything that looks like a chapter."""
    found: list[Chapter] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "chapterId" in node and ("chapterName" in node or "chapterTitle" in node):
                raw_index = node.get("chapterIndex") or node.get("index")
                try:
                    index = int(raw_index) if raw_index is not None else None
                except (TypeError, ValueError):
                    index = None
                locked = bool(
                    node.get("isVip") or node.get("isLocked") or node.get("chapterLevel")
                ) and not node.get("isAuth", False)
                found.append(
                    Chapter(
                        id=str(node["chapterId"]),
                        title=str(node.get("chapterName") or node.get("chapterTitle")).strip(),
                        index=index,
                        locked=locked,
                        book_id_hint=book_id,
                    )
                )
                return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return _dedupe(found)


def parse_catalog_html(html: str, book_id: str) -> list[Chapter]:
    """Pulls chapter links out of the catalog page, in page order."""
    soup = BeautifulSoup(html, "html.parser")
    pattern = re.compile(rf"/book/(?:[^/]*_)?{book_id}/(?:[^/?#]*_)?(\d+)")
    chapters: list[Chapter] = []
    for link in soup.find_all("a", href=True):
        match = pattern.search(link["href"])
        if not match:
            continue
        title = (link.get("title") or link.get_text(" ", strip=True)).strip()
        if not title:
            continue
        index_match = re.match(r"(?:Chapter\s*)?(\d+)", title, re.IGNORECASE)
        locked = bool(link.select_one("svg, ._lock, .lock, [class*=lock]"))
        chapters.append(
            Chapter(
                id=match.group(1),
                title=re.sub(r"\s+", " ", title),
                index=int(index_match.group(1)) if index_match else None,
                locked=locked,
                book_id_hint=book_id,
            )
        )
    return _dedupe(chapters)


def _dedupe(chapters: list[Chapter]) -> list[Chapter]:
    seen: set[str] = set()
    unique = []
    for chapter in chapters:
        if chapter.id not in seen:
            seen.add(chapter.id)
            unique.append(chapter)
    if all(c.index is not None for c in unique):
        unique.sort(key=lambda c: c.index)  # type: ignore[arg-type, return-value]
    return unique


# ---------------------------------------------------------------- network


class FetchError(RuntimeError):
    pass


async def fetch_chapters(session: aiohttp.ClientSession, book_id: str) -> list[Chapter]:
    """Returns the full chapter list, oldest first. Raises FetchError on failure."""
    errors = []

    # 1) JSON endpoint. It needs the _csrfToken cookie that the book page sets.
    try:
        async with session.get(f"{BASE}/book/{book_id}", headers=HEADERS) as resp:
            book_status = resp.status
            await resp.read()
        token = None
        for cookie in session.cookie_jar:
            if cookie.key == "_csrfToken":
                token = cookie.value
        if token:
            params = {"_csrfToken": token, "bookId": book_id, "pageIndex": "0"}
            async with session.get(
                f"{BASE}/go/pcm/chapter/get-chapter-list", params=params, headers=HEADERS
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    chapters = parse_chapter_json(data, book_id)
                    if chapters:
                        return chapters
                    errors.append("JSON endpoint returned no chapters")
                else:
                    errors.append(f"JSON endpoint HTTP {resp.status}")
        else:
            errors.append(f"no _csrfToken cookie (book page HTTP {book_status})")
    except (aiohttp.ClientError, ValueError) as exc:
        errors.append(f"JSON endpoint error: {exc!r}")

    # 2) Catalog page HTML.
    try:
        async with session.get(f"{BASE}/book/{book_id}/catalog", headers=HEADERS) as resp:
            if resp.status != 200:
                body = (await resp.text())[:200].replace("\n", " ")
                errors.append(f"catalog HTTP {resp.status} ({body})")
            else:
                chapters = parse_catalog_html(await resp.text(), book_id)
                if chapters:
                    return chapters
                errors.append("catalog page had no chapter links")
    except aiohttp.ClientError as exc:
        errors.append(f"catalog error: {exc!r}")

    raise FetchError("; ".join(errors))
