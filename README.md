# Delivery brief generator

A small Python tool that turns rough notes and a session length into a structured delivery brief for a teacher, speaker, or trainer. The brief is JSON: a title, the duration, timed beats, phrases to keep, and a do-not list.

The model is told to use only the notes. Emails, phone numbers, honorific names, and names written after a role label are redacted before the notes are sent, and again on the JSON that comes back.

## Run

Python 3.11 or newer.

```powershell
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set a key. From this directory:

```powershell
python -m briefgen --notes examples/short_talk.txt --minutes 8
```

Write the brief to a file:

```powershell
python -m briefgen --notes examples/classroom_lesson.txt --minutes 40 -o brief.json
```

`--notes` is a UTF-8 text file. `--minutes` is the session length and becomes `total_minutes`. Redaction counts print on stderr. The JSON prints on stdout.

Check the schema, the redaction step, and the sample briefs without calling a model:

```powershell
python -m unittest discover -s tests -t .
```

## Example input and output

Three note files live in `examples/`, each with a sample brief beside it.

| Notes | Minutes | Sample brief |
| --- | --- | --- |
| Classroom lesson | 40 | `examples/classroom_lesson.brief.json` |
| Short talk | 8 | `examples/short_talk.brief.json` |
| Training session | 90 | `examples/training_session.brief.json` |

The sample briefs match the schema and repeat wording from the notes, so you can read the shape before you call an API. They are hand-written samples, and a live run will differ. Regenerate one after you set a key:

```powershell
python -m briefgen --notes examples/short_talk.txt --minutes 8 -o examples/short_talk.brief.json
```

Short talk notes (`examples/short_talk.txt`):

```text
Lightning talk: Read the room before the slide
Meetup. 8 minutes hard stop.

Opening line: "The slide is not the talk."

Points:
- Last month I opened on a chart and the front row was still finding seats.
- I now wait until notebooks are open, then say the opening line.
- One story only: the chart about onboarding drop-off. Don't show the second chart.
- Close by repeating "The slide is not the talk." Then stop. No Q&A.
- Contact if they want the notes: j.okonkwo@northline.io

Speaker: Jordan Okonkwo
Do not apologize for the time limit.
Do not add a demo.
```

Sample brief (`examples/short_talk.brief.json`):

```json
{
  "title": "Read the room before the slide",
  "total_minutes": 8,
  "beats": [
    {
      "minute": 0,
      "label": "Opening line",
      "key_points": [
        "Last month I opened on a chart and the front row was still finding seats.",
        "I now wait until notebooks are open, then say the opening line.",
        "The slide is not the talk."
      ],
      "whisper_cue": "The slide is not the talk."
    },
    {
      "minute": 2,
      "label": "One story only",
      "key_points": [
        "One story only: the chart about onboarding drop-off.",
        "Don't show the second chart."
      ],
      "whisper_cue": "Don't show the second chart."
    },
    {
      "minute": 6,
      "label": "Then stop",
      "key_points": [
        "Close by repeating \"The slide is not the talk.\"",
        "Then stop. No Q&A."
      ],
      "whisper_cue": "Then stop. No Q&A."
    }
  ],
  "key_phrases": [
    "The slide is not the talk.",
    "Don't show the second chart.",
    "No Q&A."
  ],
  "do_not": [
    "Don't show the second chart.",
    "No Q&A.",
    "Do not apologize for the time limit.",
    "Do not add a demo."
  ],
  "notes": "8 minutes hard stop."
}
```

On a live run the contact line is redacted first, so the model sees `[EMAIL]` and `Speaker: [NAME]` in place of the address and the speaker's name.

## Schema

`response_format` is `json_schema` with `strict: true`. The schema is `briefgen.schema.BRIEF_SCHEMA`.

| Field | Meaning |
| --- | --- |
| `title` | Short title copied from the notes. |
| `total_minutes` | The duration you passed in. |
| `beats` | Ordered beats. `minute` is the start time, then `label`, `key_points`, and `whisper_cue`. |
| `key_phrases` | Phrases copied from the notes. |
| `do_not` | Prohibitions written in the notes. Empty when the notes list none. |
| `notes` | A leftover reminder copied from the notes, or `""`. |

The local check rejects a brief whose `total_minutes` differs from `--minutes`, or whose beat times fall outside `0 .. minutes-1`.

## Provider

The only network call is `briefgen/llm.py`. It uses the OpenAI Python client, `chat.completions.create`, and the JSON schema above. Switching hosts is a base URL and a model name. The brief code stays the same.

The default host is [SpaceXAI](https://docs.x.ai) (the xAI API):

- Base URL: `https://api.x.ai/v1`
- Model: `grok-4.7`
- Key: `XAI_API_KEY`

This client is built to drop in [Meta Model API](https://dev.meta.ai/docs/sdks). Meta speaks the same OpenAI Chat Completions shape, including `response_format` JSON schema. Change the base URL and the model:

- Base URL: `https://api.meta.ai/v1`
- Model: `muse-spark-1.3`
- Key: `MODEL_API_KEY`

```powershell
$env:MODEL_API_KEY = "your-meta-key"
$env:BRIEF_BASE_URL = "https://api.meta.ai/v1"
$env:BRIEF_MODEL = "muse-spark-1.3"
python -m briefgen --notes examples/training_session.txt --minutes 90
```

Key lookup order is `BRIEF_API_KEY`, then `XAI_API_KEY`, then `MODEL_API_KEY`, then `OPENAI_API_KEY`. A `.env` file in the current directory fills any of those that are unset. If `MODEL_API_KEY` is the only key and `BRIEF_BASE_URL` is still the SpaceXAI default, the tool stops and asks for the Meta base URL and model.

## Redaction

The redaction step is deliberately small:

- Email addresses become `[EMAIL]`.
- Phone numbers with separators, such as `510-555-0142`, become `[PHONE]`.
- `Mr`, `Mrs`, `Ms`, `Mx`, `Dr`, `Prof`, and `Professor` plus a name become `[NAME]`.
- A name after a role label (`Teacher:`, `Speaker:`, `Student:`, and the same kind of label) becomes `[NAME]`.

A name with no label and no honorific is left as written. This pass covers those obvious patterns.

## Library

```python
from briefgen import generate_brief

brief = generate_brief(open("notes.txt", encoding="utf-8").read(), minutes=40)
```

`generate_brief` redacts, calls the model, redacts the JSON strings, and checks the schema. Pass `complete=` to supply your own callable and skip the network. That callable receives the chat `messages` list and returns a JSON string.
