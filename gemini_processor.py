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

from log import parse_json_response

MODEL = "gemini-2.5-flash"
SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "dog_system.md"
_SYSTEM_PROMPT = SYSTEM_PROMPT_PATH.read_text()

_client: genai.Client | None = None


def _make_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")
        _client = genai.Client(api_key=api_key)
    return _client


def _upload_and_wait(client: genai.Client, path: str) -> types.File:
    """Upload a file to Gemini Files API and poll until ACTIVE."""
    file = client.files.upload(file=path)
    while file.state.name == "PROCESSING":
        time.sleep(2)
        file = client.files.get(name=file.name)
    if file.state.name == "FAILED":
        raise RuntimeError(f"Gemini file processing failed: {file.name}")
    return file


def analyze_video(video_path: str, current_behaviors: list[dict], session_id: int) -> dict:
    """
    TRAIN mode: upload video to Gemini Files API, analyze as dog POV, return updated behaviors.
    Returns the same JSON schema as agent.analyze_training_session().
    """
    client = _make_client()
    uploaded = _upload_and_wait(client, video_path)

    timestamp = datetime.now(timezone.utc).isoformat()
    behaviors_json = json.dumps(current_behaviors, indent=2)

    prompt = (
        f"## MODE: TRAIN\n\n"
        f"session_id: {session_id}\n"
        f"timestamp: {timestamp}\n\n"
        f"## Current Learned Behaviors\n```json\n{behaviors_json}\n```\n\n"
        "Produce your TRAIN mode JSON response. "
        "Also include a 'timeline' array of 4-6 key moments from the video. "
        "Each entry: {\"time\": \"M:SS\", \"event\": \"<dog POV, no human words>\", "
        "\"state\": \"alert|confident|happy|confused\"}. "
        "Use 'alert' when noticing a new sound/gesture, 'confident' when performing a known action, "
        "'happy' when reward is received, 'confused' when signals are contradictory or unclear."
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=[uploaded, prompt],
        config=types.GenerateContentConfig(system_instruction=_SYSTEM_PROMPT),
    )

    try:
        client.files.delete(name=uploaded.name)
    except Exception:
        pass

    return parse_json_response(response.text)


def respond_to_command(audio_path: str, current_behaviors: list[dict]) -> dict:
    """
    COMMAND mode: upload audio to Gemini Files API, match to learned behaviors, narrate response.
    Returns the same JSON schema as agent.respond_to_command(), plus 'command_transcript'.
    """
    client = _make_client()
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
        config=types.GenerateContentConfig(system_instruction=_SYSTEM_PROMPT),
    )

    try:
        client.files.delete(name=uploaded.name)
    except Exception:
        pass

    result = parse_json_response(response.text)
    if "command_transcript" not in result:
        result["command_transcript"] = ""
    return result
