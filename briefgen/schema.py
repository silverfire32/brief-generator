"""JSON schema and local checks for a delivery brief."""

from __future__ import annotations

BRIEF_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {
            "type": "string",
            "description": "Short title copied from the notes.",
        },
        "total_minutes": {
            "type": "integer",
            "description": "Session length. Must equal the duration in the user message.",
        },
        "beats": {
            "type": "array",
            "description": "Ordered beats. minute is the start time.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "minute": {
                        "type": "integer",
                        "description": "Start minute, from 0 up to but not including total_minutes.",
                    },
                    "label": {
                        "type": "string",
                        "description": "Short beat name using words from the notes.",
                    },
                    "key_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Points to say, each copied from the notes.",
                    },
                    "whisper_cue": {
                        "type": "string",
                        "description": "One short glanceable line copied from the notes.",
                    },
                },
                "required": ["minute", "label", "key_points", "whisper_cue"],
            },
        },
        "key_phrases": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Phrases copied from the notes.",
        },
        "do_not": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Prohibitions written in the notes. Empty array if the notes list none.",
        },
        "notes": {
            "type": "string",
            "description": "Leftover reminder copied from the notes, or an empty string.",
        },
    },
    "required": [
        "title",
        "total_minutes",
        "beats",
        "key_phrases",
        "do_not",
        "notes",
    ],
}

_BEAT_FIELDS = ("minute", "label", "key_points", "whisper_cue")


class BriefError(ValueError):
    """The brief is missing, mistyped, or outside the requested duration."""


def _strings(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise BriefError(f"{field} must be an array of strings.")
    return value


def validate_brief(data: object, minutes: int) -> dict:
    """Return data when it matches the brief schema and the requested duration."""
    if not isinstance(data, dict):
        raise BriefError("Brief is not a JSON object.")
    missing = [key for key in BRIEF_SCHEMA["required"] if key not in data]
    if missing:
        raise BriefError(f"Brief is missing {', '.join(missing)}.")
    extra = [key for key in data if key not in BRIEF_SCHEMA["required"]]
    if extra:
        raise BriefError(f"Brief has unexpected fields: {', '.join(extra)}.")
    if minutes < 1:
        raise BriefError("minutes must be at least 1.")

    title = data["title"]
    if not isinstance(title, str) or not title.strip():
        raise BriefError("title must be a non-empty string.")
    total = data["total_minutes"]
    if isinstance(total, bool) or not isinstance(total, int):
        raise BriefError("total_minutes must be an integer.")
    if total != minutes:
        raise BriefError(f"total_minutes is {total}, expected {minutes}.")

    beats = data["beats"]
    if not isinstance(beats, list) or not beats:
        raise BriefError("beats must be a non-empty array.")

    last_minute = -1
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict):
            raise BriefError(f"beats[{index}] must be an object.")
        beat_extra = [key for key in beat if key not in _BEAT_FIELDS]
        if beat_extra:
            raise BriefError(
                f"beats[{index}] has unexpected fields: {', '.join(beat_extra)}."
            )
        for field in _BEAT_FIELDS:
            if field not in beat:
                raise BriefError(f"beats[{index}] is missing {field}.")
        minute = beat["minute"]
        if isinstance(minute, bool) or not isinstance(minute, int):
            raise BriefError(f"beats[{index}].minute must be an integer.")
        if not 0 <= minute < minutes:
            raise BriefError(
                f"beats[{index}].minute is {minute}; it must be from 0 up to {minutes - 1}."
            )
        if minute < last_minute:
            raise BriefError("beats must be in time order.")
        last_minute = minute
        label = beat["label"]
        if not isinstance(label, str) or not label.strip():
            raise BriefError(f"beats[{index}].label must be a non-empty string.")
        _strings(beat["key_points"], f"beats[{index}].key_points")
        if not isinstance(beat["whisper_cue"], str):
            raise BriefError(f"beats[{index}].whisper_cue must be a string.")

    _strings(data["key_phrases"], "key_phrases")
    _strings(data["do_not"], "do_not")
    if not isinstance(data["notes"], str):
        raise BriefError("notes must be a string.")
    return data
