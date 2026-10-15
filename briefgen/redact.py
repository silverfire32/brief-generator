"""Replace obvious emails, phone numbers, and labeled names."""

from __future__ import annotations

import re
from dataclasses import dataclass

# The role word is case-insensitive. The name stays case-sensitive and
# stays on one line, so "Name the three steps" is left alone.
_LABELED_NAME = re.compile(
    r"(?P<label>(?i:\b(?:teacher|student|presenter|speaker|trainer|instructor|"
    r"facilitator|host|contact|name|author|parent|guardian)\b))"
    r"(?P<sep>[ \t]*[:\-][ \t]*)"
    r"(?P<name>[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){0,2})"
)
_HONORIFIC = re.compile(
    r"\b(?:Mr|Mrs|Ms|Mx|Dr|Prof|Professor)\.?[ \t]+[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){0,2}\b"
)
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
# Separators are required so years, durations, and fractions stay intact.
_PHONE = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[ \t.\-]?)?(?:\(\d{3}\)|\d{3})[ \t.\-]\d{3}[ \t.\-]\d{4}(?!\w)"
)


@dataclass(frozen=True)
class RedactionResult:
    text: str
    emails: int = 0
    phones: int = 0
    names: int = 0

    @property
    def total(self) -> int:
        return self.emails + self.phones + self.names

    def summary(self) -> str:
        parts: list[str] = []
        if self.emails:
            parts.append(f"{self.emails} email" + ("s" if self.emails != 1 else ""))
        if self.phones:
            parts.append(f"{self.phones} phone number" + ("s" if self.phones != 1 else ""))
        if self.names:
            parts.append(f"{self.names} name" + ("s" if self.names != 1 else ""))
        if not parts:
            return ""
        return "Redacted " + ", ".join(parts) + "."


def _labeled(match: re.Match[str]) -> str:
    return f"{match.group('label')}{match.group('sep')}[NAME]"


def redact_text(text: str) -> RedactionResult:
    """Replace obvious contacts and names. Unlabeled names are kept."""
    emails = phones = names = 0
    text, emails = _EMAIL.subn("[EMAIL]", text)
    text, phones = _PHONE.subn("[PHONE]", text)
    text, names = _HONORIFIC.subn("[NAME]", text)
    text, labeled = _LABELED_NAME.subn(_labeled, text)
    names += labeled
    return RedactionResult(text=text, emails=emails, phones=phones, names=names)


def redact_value(value: object) -> object:
    """Run redact_text on every string inside a JSON-like value."""
    if isinstance(value, str):
        return redact_text(value).text
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_value(item) for key, item in value.items()}
    return value
