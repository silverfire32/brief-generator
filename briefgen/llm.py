"""The only provider call. Swap hosts with BRIEF_BASE_URL and BRIEF_MODEL.

Default host is SpaceXAI (xAI): https://api.x.ai/v1 and grok-4.7.
Meta Model API drop-in: https://api.meta.ai/v1 and muse-spark-1.3.
"""

from __future__ import annotations

import os
from pathlib import Path

from briefgen.schema import BRIEF_SCHEMA

DEFAULT_BASE_URL = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-4.7"
META_BASE_URL = "https://api.meta.ai/v1"
META_MODEL = "muse-spark-1.3"

_KEY_NAMES = ("BRIEF_API_KEY", "XAI_API_KEY", "MODEL_API_KEY", "OPENAI_API_KEY")


class ProviderError(RuntimeError):
    """The model call is not configured or returned nothing usable."""


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE lines from .env without overriding existing variables."""
    file = path or Path.cwd() / ".env"
    if not file.is_file():
        return
    for raw in file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_config() -> tuple[str, str, str]:
    """Return (api_key, base_url, model) for the OpenAI-compatible client."""
    load_dotenv()
    present = {name: os.environ.get(name, "").strip() for name in _KEY_NAMES}
    api_key = next((present[name] for name in _KEY_NAMES if present[name]), "")
    base_url = os.environ.get("BRIEF_BASE_URL", "").strip() or DEFAULT_BASE_URL
    model = os.environ.get("BRIEF_MODEL", "").strip()

    meta_key_only = bool(present["MODEL_API_KEY"]) and not any(
        present[name] for name in ("BRIEF_API_KEY", "XAI_API_KEY", "OPENAI_API_KEY")
    )
    if meta_key_only and base_url.rstrip("/") == DEFAULT_BASE_URL.rstrip("/"):
        raise ProviderError(
            "MODEL_API_KEY is set, but the client is still aimed at SpaceXAI. "
            f"Set BRIEF_BASE_URL={META_BASE_URL} and BRIEF_MODEL={META_MODEL}."
        )
    if not api_key:
        raise ProviderError(
            "No API key. Set XAI_API_KEY for SpaceXAI, or MODEL_API_KEY plus "
            f"BRIEF_BASE_URL={META_BASE_URL} and BRIEF_MODEL={META_MODEL} for Meta Model API."
        )
    if not model:
        model = META_MODEL if "api.meta.ai" in base_url else DEFAULT_MODEL
    return api_key, base_url, model


def chat_json(messages: list[dict]) -> str:
    """Call chat completions and return the schema-constrained JSON text."""
    api_key, base_url, model = resolve_config()
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ProviderError(
            "Install the openai package: python -m pip install -r requirements.txt"
        ) from exc
    client = OpenAI(api_key=api_key, base_url=base_url)
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "delivery_brief",
                "strict": True,
                "schema": BRIEF_SCHEMA,
            },
        },
    )
    content = completion.choices[0].message.content
    if not content or not content.strip():
        raise ProviderError("The model returned an empty brief.")
    return content
