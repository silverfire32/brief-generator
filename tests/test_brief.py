import io
import json
import os
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from briefgen.generate import SYSTEM_PROMPT, generate_brief, parse_model_json
from briefgen.llm import ProviderError, resolve_config
from briefgen.redact import redact_text
from briefgen.schema import BriefError, validate_brief

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
_CONFIG_KEYS = (
    "BRIEF_API_KEY",
    "XAI_API_KEY",
    "MODEL_API_KEY",
    "OPENAI_API_KEY",
    "BRIEF_BASE_URL",
    "BRIEF_MODEL",
)


def _sample(name: str) -> dict:
    return {
        "title": name,
        "total_minutes": 10,
        "beats": [
            {
                "minute": 0,
                "label": "Open",
                "key_points": ["start"],
                "whisper_cue": "start",
            }
        ],
        "key_phrases": [],
        "do_not": [],
        "notes": "",
    }


class BriefTests(unittest.TestCase):
    def test_prompt_limits_the_model_to_the_notes(self) -> None:
        self.assertIn("Use only information from the notes.", SYSTEM_PROMPT)
        self.assertIn("Do not invent facts", SYSTEM_PROMPT)
        self.assertIn("or phrases", SYSTEM_PROMPT)

    def test_fenced_json_parses(self) -> None:
        payload = _sample("Fenced")
        text = "```json\n" + json.dumps(payload) + "\n```"
        self.assertEqual(parse_model_json(text)["title"], "Fenced")

    def test_rejects_minute_outside_the_session(self) -> None:
        payload = _sample("Late")
        payload["beats"][0]["minute"] = 10
        with self.assertRaises(BriefError):
            validate_brief(payload, 10)

    def test_generate_redacts_before_the_call_and_on_the_way_out(self) -> None:
        seen: list[str] = []

        def complete(messages: list[dict]) -> str:
            seen.append(messages[0]["content"])
            seen.append(messages[1]["content"])
            payload = _sample("Fractions")
            payload["notes"] = "Reply to secret@school.edu"
            payload["beats"][0]["whisper_cue"] = "Ask Ms. Alvarez"
            return json.dumps(payload)

        brief = generate_brief(
            "Teacher: Ms. Alvarez secret@school.edu\nAim: fractions.",
            10,
            complete=complete,
        )
        self.assertIn("Use only information from the notes.", seen[0])
        self.assertIn("Duration in minutes: 10", seen[1])
        self.assertNotIn("secret@school.edu", seen[1])
        self.assertNotIn("Alvarez", seen[1])
        self.assertIn("[EMAIL]", seen[1])
        self.assertEqual(brief["notes"], "Reply to [EMAIL]")
        self.assertEqual(brief["beats"][0]["whisper_cue"], "Ask [NAME]")
        self.assertEqual(brief["total_minutes"], 10)

    def test_example_contacts_are_redacted(self) -> None:
        classroom = redact_text((EXAMPLES / "classroom_lesson.txt").read_text(encoding="utf-8"))
        talk = redact_text((EXAMPLES / "short_talk.txt").read_text(encoding="utf-8"))
        training = redact_text((EXAMPLES / "training_session.txt").read_text(encoding="utf-8"))
        self.assertNotIn("Maya Chen", classroom.text)
        self.assertNotIn("Alvarez", classroom.text)
        self.assertNotIn("@", classroom.text)
        self.assertNotIn("510-555-0142", classroom.text)
        self.assertNotIn("j.okonkwo@northline.io", talk.text)
        self.assertNotIn("Jordan Okonkwo", talk.text)
        self.assertNotIn("Priya", training.text)
        self.assertNotIn("priya.shah@harborpay.com", training.text)
        self.assertNotIn("628-555-0177", training.text)
        self.assertIn("listen, restate, offer the next step.", training.text)

    def test_examples_stay_inside_the_notes(self) -> None:
        pairs = {
            "classroom_lesson": 40,
            "short_talk": 8,
            "training_session": 90,
        }
        self.assertEqual(len(list(EXAMPLES.glob("*.brief.json"))), 3)
        for stem, minutes in pairs.items():
            notes = (EXAMPLES / f"{stem}.txt").read_text(encoding="utf-8")
            brief = json.loads((EXAMPLES / f"{stem}.brief.json").read_text(encoding="utf-8"))
            validate_brief(brief, minutes)
            source = redact_text(notes).text
            strings = [brief["title"], brief["notes"], *brief["key_phrases"], *brief["do_not"]]
            for beat in brief["beats"]:
                strings.append(beat["label"])
                strings.append(beat["whisper_cue"])
                strings.extend(beat["key_points"])
            for text in strings:
                if text:
                    self.assertIn(text, source, f"{stem}: {text!r}")


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {key: os.environ.get(key) for key in _CONFIG_KEYS}
        for key in _CONFIG_KEYS:
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_default_is_spacexai(self) -> None:
        os.environ["XAI_API_KEY"] = "test-key"
        api_key, base_url, model = resolve_config()
        self.assertEqual(api_key, "test-key")
        self.assertEqual(base_url, "https://api.x.ai/v1")
        self.assertEqual(model, "grok-4.7")

    def test_meta_drop_in_is_base_url_and_model(self) -> None:
        os.environ["MODEL_API_KEY"] = "meta-key"
        os.environ["BRIEF_BASE_URL"] = "https://api.meta.ai/v1"
        os.environ["BRIEF_MODEL"] = "muse-spark-1.3"
        api_key, base_url, model = resolve_config()
        self.assertEqual(api_key, "meta-key")
        self.assertEqual(base_url, "https://api.meta.ai/v1")
        self.assertEqual(model, "muse-spark-1.3")

    def test_meta_key_without_base_url_is_refused(self) -> None:
        os.environ["MODEL_API_KEY"] = "meta-key"
        with self.assertRaises(ProviderError):
            resolve_config()

    def test_cli_reports_a_missing_key(self) -> None:
        from briefgen.__main__ import main

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = main(["--notes", str(EXAMPLES / "short_talk.txt"), "--minutes", "8"])
        self.assertEqual(code, 1)
        message = stderr.getvalue()
        self.assertIn("Redacted 1 email, 1 name.", message)
        self.assertIn("No API key", message)


if __name__ == "__main__":
    unittest.main()
