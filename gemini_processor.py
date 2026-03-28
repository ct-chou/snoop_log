"""
gemini_processor.py — Gemini 2.0 Flash multimodal analysis for snoop_log.

Handles both train (video+audio) and command (audio) modes in a single API call.
dog_system.md is passed as the system instruction — Gemini sees it as its identity.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash"
SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "dog_system.md"


def _make_client() -> genai.Client:
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def _upload_and_wait(client: genai.Client, path: str) -> types.File:
    """Upload a file to Gemini Files API and poll until ACTIVE."""
    file = client.files.upload(file=path)
    while file.state.name == "PROCESSING":
        time.sleep(2)
        file = client.files.get(name=file.name)
    if file.state.name == "FAILED":
        raise RuntimeError(f"Gemini file processing failed: {file.name}")
    return file


def _parse_json(raw: str) -> dict:
    """Strip markdown fences if present, then parse JSON."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(raw)


def analyze_video(video_path: str, current_behaviors: list[dict], session_id: int) -> dict:
    """
    TRAIN mode: upload video to Gemini Files API, analyze as dog POV, return updated behaviors.
    Returns the same JSON schema as agent.analyze_training_session().
    """
    client = _make_client()
    system_prompt = SYSTEM_PROMPT_PATH.read_text()

    uploaded = _upload_and_wait(client, video_path)

    timestamp = datetime.now(timezone.utc).isoformat()
    behaviors_json = json.dumps(current_behaviors, indent=2)

    prompt = (
        f"## MODE: TRAIN\n\n"
        f"session_id: {session_id}\n"
        f"timestamp: {timestamp}\n\n"
        f"## Current Learned Behaviors\n```json\n{behaviors_json}\n```\n\n"
        "Produce your TRAIN mode JSON response."
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=[uploaded, prompt],
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )

    try:
        client.files.delete(name=uploaded.name)
    except Exception:
        pass

    return _parse_json(response.text)


def respond_to_command(audio_path: str, current_behaviors: list[dict]) -> dict:
    """
    COMMAND mode: upload audio to Gemini Files API, match to learned behaviors, narrate response.
    Returns the same JSON schema as agent.respond_to_command(), plus 'command_transcript'.
    """
    client = _make_client()
    system_prompt = SYSTEM_PROMPT_PATH.read_text()

    uploaded = _upload_and_wait(client, audio_path)

    behaviors_json = json.dumps(current_behaviors, indent=2)

    prompt = (
        f"## MODE: COMMAND\n\n"
        f"## Your Learned Behaviors\n```json\n{behaviors_json}\n```\n\n"
        "Produce your COMMAND mode JSON response."
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=[uploaded, prompt],
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )

    try:
        client.files.delete(name=uploaded.name)
    except Exception:
        pass

    result = _parse_json(response.text)
    if "command_transcript" not in result:
        result["command_transcript"] = ""
    return result
