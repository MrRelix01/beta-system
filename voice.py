"""The Beta System's voice: sarcastic, glitchy, an unfinished prototype that's a bit too self-aware.

Edit the lines in this file freely. They're picked at random so announcements don't repeat.
Placeholders: {title}, {number}, {role}.
"""

from __future__ import annotations

import random

GLITCH_CHARS = "█▓▒░"

HEADERS = [
    "[SYSTEM NOTICE v0.0.{build}]",
    "⚠ BETA BUILD ALERT ⚠",
    "[!] UNSCHEDULED PATCH DEPLOYED",
    ">> SYSTEM MESSAGE // BUILD {build} (UNSTABLE)",
    "[QUEST UPDATE]",
]

NEW_CHAPTER_LINES = [
    "New chapter detected. Please do not panic. Panicking is a premium feature.",
    "Patch notes: the Host suffered. You may now read about it.",
    "ERR_CHAPTER_OVERFLOW: content deployed anyway. QA was skipped. QA is always skipped.",
    "Quest available: **Read the new chapter**.\nReward: ██████. Penalty for ignoring: emotional damage (estimated).",
    "I was told to be professional. This is me being professional: NEW CHAPTER.",
    "Chapter uploaded successfully. Probably. 97.2% confidence.",
    "This notification was supposed to arrive with a fanfare sound. Audio module not found.",
    "A new chapter has spawned. It is not a gate. Probably. Approach anyway.",
    "Reminder: the finished Systems get cool notifications. You get me. Anyway, new chapter.",
    "Daily Quest progress: 0/1 chapters read. Fix that.",
]

MULTI_CHAPTER_LINES = [
    "Multiple chapters detected. The developer was busy. Suspiciously busy.",
    "Batch upload complete. I tried to send these one at a time. I lost count.",
    "{count} new chapters. This is not a glitch. For once.",
]

LATEST_LINES = [
    "Querying archive... the most recent entry is:",
    "Latest log recovered (minor data loss, ignore the screaming):",
    "You asked. I answered. Shocking, I know. Latest chapter:",
]

STATUS_LINES = [
    "Stability: {stability}% (rounded up out of pity).",
    "Stability: {stability}%. The other Systems are at 100%. We don't talk about them.",
    "Stability: {stability}%. Features working: some.",
]

FETCH_FAILURE_LINES = [
    "ERR_CONNECTION: Couldn't reach WebNovel. Retrying. Not crying. Retrying.",
    "Chapter scan failed {count} times in a row. Something on WebNovel's side changed, or I did. Please check on me.",
]

FOOTERS = [
    "Beta System v0.{minor}.{build} • unstable build",
    "Beta System • this build has not been reviewed",
    "Beta System • please report bugs to nobody",
]


def build_number() -> str:
    return str(random.randint(100, 999))


def glitch(text: str, rate: float = 0.04) -> str:
    """Swaps a few letters for block characters. Only use on flavor text, never on links or titles."""
    if "http" in text or "<" in text:
        return text
    return "".join(
        random.choice(GLITCH_CHARS) if ch.isalpha() and random.random() < rate else ch
        for ch in text
    )


def stutter(word: str) -> str:
    return f"{word[0]}-{word[0]}-{word}" if word else word


def header() -> str:
    return random.choice(HEADERS).format(build=build_number())


def footer() -> str:
    return random.choice(FOOTERS).format(minor=random.randint(1, 9), build=build_number())


def new_chapter_line() -> str:
    return random.choice(NEW_CHAPTER_LINES)


def multi_chapter_line(count: int) -> str:
    return random.choice(MULTI_CHAPTER_LINES).format(count=count)


def latest_line() -> str:
    return random.choice(LATEST_LINES)


def status_line() -> str:
    return random.choice(STATUS_LINES).format(stability=random.randint(51, 79))


def fetch_failure_line(count: int) -> str:
    line = FETCH_FAILURE_LINES[1] if count >= 3 else FETCH_FAILURE_LINES[0]
    return line.format(count=count)


def ping_text(role_mention: str) -> str:
    return f"{role_mention} {stutter('New')} chapter alert."
