"""
agent.py — Claude API calls for training analysis and command response.
"""

import json
import os
import base64
from datetime import datetime, timezone
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-4-6"
SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "dog_system.md"


def _load_system_prompt() -> str:
    with open(SYSTEM_PROMPT_PATH) as f:
        return f.read()


def _parse_json_response(raw: str) -> dict:
    """Strip markdown fences if present, then parse JSON."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(raw)


def transcribe_audio(audio_path: str, client: anthropic.Anthropic) -> str:
    """
    Send an audio file to Claude and get a transcript with tone/emphasis annotations.
    Returns plain text describing sounds, tone, and repetition — not words.
    """
    with open(audio_path, "rb") as f:
        audio_data = base64.standard_b64encode(f.read()).decode("utf-8")

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "audio/mpeg",
                            "data": audio_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Transcribe this audio from a dog training session. "
                            "For each spoken command or sound, note: the exact word(s) said, "
                            "the tone (firm/gentle/excited/frustrated/neutral), "
                            "and how many times it was repeated. "
                            "Also note non-verbal sounds (clicker, whistle, treat bag, petting sounds, etc.). "
                            "Format: [tone, xN] 'words' — e.g. [firm, x3] 'Sit!' [treat bag rustling] [gentle] 'Good boy!'"
                        ),
                    },
                ],
            }
        ],
    )
    return response.content[0].text


def analyze_training_session(
    frames_b64: list[str],
    transcript: str,
    current_behaviors: list[dict],
    session_id: int,
    client: anthropic.Anthropic,
) -> dict:
    """
    TRAIN mode: analyze a session and return updated behavior associations.
    """
    system_prompt = _load_system_prompt()
    timestamp = datetime.now(timezone.utc).isoformat()
    behaviors_json = json.dumps(current_behaviors, indent=2)

    content = []

    for frame_b64 in frames_b64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": frame_b64,
            },
        })

    content.append({
        "type": "text",
        "text": (
            f"## MODE: TRAIN\n\n"
            f"session_id: {session_id}\n"
            f"timestamp: {timestamp}\n\n"
            f"## Audio Transcript (tone-annotated)\n{transcript}\n\n"
            f"## Current Learned Behaviors\n```json\n{behaviors_json}\n```\n\n"
            "Produce your TRAIN mode JSON response."
        ),
    })

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
    )

    return _parse_json_response(response.content[0].text)


def respond_to_command(
    command_audio_path: str,
    current_behaviors: list[dict],
    client: anthropic.Anthropic,
) -> dict:
    """
    COMMAND mode: hear an audio command, match to learned behaviors, narrate the response.
    """
    # First transcribe the command audio
    command_transcript = transcribe_audio(command_audio_path, client)

    system_prompt = _load_system_prompt()
    behaviors_json = json.dumps(current_behaviors, indent=2)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": (
                    f"## MODE: COMMAND\n\n"
                    f"## Sound/Command Just Heard\n{command_transcript}\n\n"
                    f"## Your Learned Behaviors\n```json\n{behaviors_json}\n```\n\n"
                    "Produce your COMMAND mode JSON response."
                ),
            }
        ],
    )

    result = _parse_json_response(response.content[0].text)
    result["command_transcript"] = command_transcript
    return result
