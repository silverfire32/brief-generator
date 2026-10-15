import unittest

from briefgen.redact import redact_text, redact_value


class RedactTests(unittest.TestCase):
    def test_email_phone_honorific_and_labeled_name(self) -> None:
        raw = (
            "Teacher: Ms. Alvarez (alvarez.m@riverside.k12.edu). "
            "If a sub calls, use 510-555-0142. "
            "Student: Maya Chen already presented yesterday."
        )
        result = redact_text(raw)
        self.assertEqual(result.emails, 1)
        self.assertEqual(result.phones, 1)
        self.assertEqual(result.names, 2)
        self.assertNotIn("alvarez.m@riverside.k12.edu", result.text)
        self.assertNotIn("510-555-0142", result.text)
        self.assertNotIn("Alvarez", result.text)
        self.assertNotIn("Maya Chen", result.text)
        self.assertIn("Teacher: [NAME]", result.text)
        self.assertIn("[EMAIL]", result.text)
        self.assertIn("[PHONE]", result.text)
        self.assertIn("Student: [NAME] already presented yesterday.", result.text)

    def test_lesson_words_and_fractions_stay(self) -> None:
        raw = "Equivalent fractions, grade 4. Show 1/2 = 2/4. Session: 40 minutes."
        result = redact_text(raw)
        self.assertEqual(result.total, 0)
        self.assertEqual(result.text, raw)

    def test_labeled_name_stops_at_the_line_break(self) -> None:
        raw = "Speaker: Jordan Okonkwo\nDo not apologize for the time limit."
        result = redact_text(raw)
        self.assertEqual(
            result.text,
            "Speaker: [NAME]\nDo not apologize for the time limit.",
        )
        self.assertEqual(result.names, 1)

    def test_name_the_three_steps_is_not_a_labeled_name(self) -> None:
        raw = "Name the three steps: listen, restate, offer the next step."
        result = redact_text(raw)
        self.assertEqual(result.names, 0)
        self.assertEqual(result.text, raw)

    def test_output_strings_are_redacted(self) -> None:
        cleaned = redact_value(
            {
                "title": "Reach ada@school.edu",
                "beats": [{"whisper_cue": "Call Ms. Alvarez"}],
            }
        )
        self.assertEqual(cleaned["title"], "Reach [EMAIL]")
        self.assertEqual(cleaned["beats"][0]["whisper_cue"], "Call [NAME]")


if __name__ == "__main__":
    unittest.main()
