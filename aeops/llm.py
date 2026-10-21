"""Thin wrapper around the model. Falls back to a canned mock when no API key
is set, so the demo and tests run offline."""
import json
import os
import re


def have_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def ask_json(system: str, prompt: str) -> dict:
    if not have_key():
        raise RuntimeError("no API key")
    import anthropic

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=os.getenv("AEOPS_MODEL", "claude-sonnet-4-5"),
        max_tokens=2000,
        system=system + "\nReply with a single JSON object and nothing else.",
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    match = re.search(r"\{.*\}", text, re.S)
    return json.loads(match.group(0))
