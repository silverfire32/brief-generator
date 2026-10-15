"""CLI: python -m briefgen --notes notes.txt --minutes 40"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from briefgen.generate import generate_brief
from briefgen.llm import ProviderError
from briefgen.redact import redact_text
from briefgen.schema import BriefError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Turn rough notes and a duration into a structured delivery brief."
    )
    parser.add_argument("--notes", required=True, help="Path to a UTF-8 text file of rough notes.")
    parser.add_argument("--minutes", required=True, type=int, help="Session duration in minutes.")
    parser.add_argument("-o", "--output", help="Write the JSON brief to this path. Default: stdout.")
    args = parser.parse_args(argv)
    if args.minutes < 1:
        parser.error("--minutes must be at least 1")

    try:
        raw = Path(args.notes).read_text(encoding="utf-8")
        report = redact_text(raw).summary()
        if report:
            print(report, file=sys.stderr)
        brief = generate_brief(raw, args.minutes)
        text = json.dumps(brief, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
    except (BriefError, ProviderError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
