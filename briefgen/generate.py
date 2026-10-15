"""Build a delivery brief from rough notes and a duration."""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from briefgen.llm import chat_json
from briefgen.redact import redact_text, redact_value
from briefgen.schema import BriefError, validate_brief

SYSTEM_PROMPT = """\
You turn rough delivery notes into a brief a teacher, speaker, or trainer can follow while they talk.

Use only information from the notes. Do not invent facts, examples, numbers, names, stories, or phrases. If a detail is not written in the notes, leave it out. A thin beat is the right result when the notes are thin.

title, label, key_points, whisper_cue, key_phrases, do_not, and notes must repeat wording from the notes. Do not paraphrase a point into a new claim.

[NAME], [EMAIL], and [PHONE] are redaction placeholders. Copy them as written. Do not guess what they replace.

total_minutes must equal the duration in the user message. beats run in time order. Each minute is when that beat starts: an integer from 0 up to, and not including, total_minutes.

do_not lists only prohibitions written in the notes. Use an empty array when the notes list none. notes is a leftover reminder copied from the notes, or an empty string.
"""

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)

Complete = Callable[[list[dict]], str]


def user_message(notes: str, minutes: int) -> str:
    return (
        f"Duration in minutes: {minutes}\n\n"
        "Notes (the only source you may use):\n"
        f"{notes.strip()}\n"
    )


def parse_model_json(content: str) -> dict:
    """Parse a JSON object, including a fenced object from a host that ignored the schema."""
    text = content.strip()
    if text.startswith("```"):
        text = _FENCE.sub("", text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BriefError(f"Model returned non-JSON ({exc.msg}).") from exc
    if not isinstance(data, dict):
        raise BriefError("Model JSON is not an object.")
    return data


def generate_brief(
    notes: str,
    minutes: int,
    *,
    complete: Complete | None = None,
) -> dict:
    """Redact the notes, request a schema-constrained brief, and validate it.

    complete replaces the provider call. Tests pass a stub. The default calls
    briefgen.llm.chat_json, which is the only place a provider is named.
    """
    if minutes < 1:
        raise BriefError("minutes must be at least 1.")
    cleaned = redact_text(notes).text
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message(cleaned, minutes)},
    ]
    content = (complete or chat_json)(messages)
    data = parse_model_json(content)
    redacted = redact_value(data)
    return validate_brief(redacted, minutes)
