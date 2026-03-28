# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

**snoop_log** is a multimodal AI agent built for a hackathon. It takes the perspective of a dog being trained by its owner. Training session videos are analyzed and stored as learned behavior associations (trigger → action). When the owner issues a command, the dog agent matches it to its learned behaviors and narrates itself performing the action in first-person dog POV.

Two execution modes:
- **Train**: video+audio of a training session → updates `behaviors.json` (confidence scores accumulate across sessions)
- **Command**: audio clip from owner → dog matches pattern → narrates performing the action

## Running the CLI

```bash
pip install -r requirements.txt
# Also requires: brew install ffmpeg

export ANTHROPIC_API_KEY=...
export GEMINI_API_KEY=...
export DO_SPACES_KEY=... DO_SPACES_SECRET=... DO_SPACES_REGION=nyc3 DO_SPACES_BUCKET=snoop-log-videos

python main.py train session1.mp4       # process a training video
python main.py command go_to_bed.mp3    # respond to an audio command
python main.py show                     # print learned behaviors table
python main.py sessions                 # print training session history
python main.py serve                    # start FastAPI webhook server (port 8080)
```

## Architecture

### Current state (implemented)
- `main.py` — CLI dispatcher. All four subcommands live here.
- `processor.py` — ffmpeg-based frame extraction + audio extraction. **Legacy path** — used as fallback when Spaces credentials are not set.
- `agent.py` — Claude API calls. **Legacy path** — superseded by `gemini_processor.py` in the integrated pipeline.
- `log.py` — local JSON persistence only. Reads/writes `sessions.json` and `behaviors.json`. No external calls.
- `prompts/dog_system.md` — the dog's system prompt, covering both TRAIN and COMMAND modes. This is the core of the dog persona. Do not change the JSON output schemas here without updating callers.

### Integration layer (to be implemented — see plan)
- `storage.py` — DigitalOcean Spaces via boto3. Object key prefixes: `uploads/` (incoming), `processed/` (done), `state/` (behaviors.json + sessions.json).
- `gemini_processor.py` — Gemini 2.0 Flash via Files API. Handles both perception AND dog-persona reasoning in one call. `dog_system.md` is passed as the Gemini system instruction. Two functions: `analyze_video()` (train) and `respond_to_command()` (command).
- `pipeline.py` — Railtracks agent pipeline. Three nodes: `node_download_video` → `node_gemini_analyze` → `node_persist_results`. Entry point: `flow = rt.Flow(...)`.
- `webhook.py` — FastAPI. `POST /webhook/train` receives Nexla triggers (new video in Spaces bucket), runs pipeline as a BackgroundTask. `GET /health` for uptime checks.

### Data flow (integrated pipeline)
```
video uploaded to DO Spaces
  → Nexla webhook → POST /webhook/train
  → Railtracks pipeline:
      download from Spaces → Gemini (full video+audio analysis, dog POV JSON) → persist to Spaces + local
  → behaviors.json updated
```

When Spaces credentials are absent, `cmd_train` falls back to the legacy path: `processor.py` (ffmpeg) + `agent.py` (Claude).

### State files
- `behaviors.json` — the dog's current learned associations. Authoritative source for the command phase. Synced to `state/behaviors.json` in Spaces after each train session.
- `sessions.json` — append-only log of training session summaries.

## PM agent

A project manager subagent is available at `.claude/agents/pm_agent.md`. Invoke it for sprint planning, backlog management, blockers, and ADRs. It maintains project docs under `docs/`, `plans/`, and `status/`.

## Key design constraint

The dog never uses human language in its reasoning. `dog_system.md` enforces this: sounds are described by tone and pattern ("short downward sound x3"), gestures by shape ("hand pointing toward floor"). Any change to the perception layer must preserve this constraint or the persona breaks.
