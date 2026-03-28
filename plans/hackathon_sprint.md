# Hackathon Sprint — snoop_log
**Date:** 2026-03-28
**Duration:** A few hours (time-boxed, single session)
**Delivery tool:** Claude Code (all coding)
**Goal:** Working demo of the full integrated pipeline — video in, Gemini processes it, behaviors.json updated, audio command narrated from dog POV.

---

## Situation Assessment

### What works right now (demo-able today without any changes)

The legacy path is fully functional end-to-end:

- `python main.py train session.mp4` — ffmpeg extracts frames + audio, Claude Sonnet 4.6 analyzes, behaviors.json updated, rich CLI output
- `python main.py command go_to_bed.mp3` — Claude matches to learned behaviors, narrates in dog POV
- `python main.py show` / `python main.py sessions` — display state

**The project already has a working demo.** The integration layer (Gemini, Spaces, pipeline, webhook) is additive infrastructure for a production story, not a prerequisite for demoing the core concept.

### What is NOT installed (runtime blockers for integration layer)

| Package | Status |
|---|---|
| anthropic | Not installed (base path broken too — install first) |
| rich | Not installed |
| google-generativeai | Not installed |
| boto3 | Not installed (botocore is present via anaconda) |
| fastapi | Not installed |
| uvicorn | Not installed |
| railtracks | Not installed |

**Critical:** Even the existing legacy CLI will fail on import until `pip install -r requirements.txt` is run. This is the first task.

### railtracks risk

`railtracks` is not a well-known public package. It may be a proprietary, internal, or fictional library. Before writing `pipeline.py` we must verify it installs and has a usable API. If it does not exist on PyPI, the pipeline node design must pivot to plain async functions or a simple sequential runner. This is the highest-risk item in the integration layer.

---

## Priority Framework

**P0 — Must demo:** Core concept works, both modes run, output is compelling.
**P1 — Nice to have:** Adds realism, shows the full architecture story.
**P2 — Skip:** Requires infrastructure not in our control (Nexla, live Spaces bucket) or adds no demo value.

---

## P0 Tasks — Must Ship (estimated ~45 min total)

These are the minimum for a credible hackathon demo.

### T-001 | Install dependencies
**Story:** Legacy path is currently broken due to missing packages.
**Action:** Run `pip install -r requirements.txt` and verify `python main.py show` exits cleanly.
**Acceptance:** `import anthropic`, `import rich`, `import ffmpeg` all succeed.
**Time estimate:** 5 min
**Owner:** Claude Code

### T-002 | Verify legacy end-to-end with a real file
**Story:** Confirm the working baseline before touching any code.
**Action:** Run `python main.py train <any short mp4>` and `python main.py command <any mp3>` against the installed environment.
**Acceptance:** Both commands complete without error, behaviors.json is written.
**Time estimate:** 10 min (includes finding/creating a test clip)
**Owner:** Human to provide test file, Claude Code to run

### T-003 | Write gemini_processor.py
**Story:** Swap Claude legacy path for Gemini 2.0 Flash native video+audio understanding.
**Two functions to implement:**
- `analyze_video(video_path, current_behaviors, session_id)` — uploads video via Gemini Files API, passes `dog_system.md` as system instruction, returns same JSON schema as `agent.py:analyze_training_session()`
- `respond_to_command(audio_path, current_behaviors)` — uploads audio via Files API, returns same schema as `agent.py:respond_to_command()`

**Key constraint:** No ffmpeg needed in the Gemini path — Gemini ingests video natively. The dog persona constraint (no human words in reasoning) is enforced by `dog_system.md` passed as system instruction.

**Acceptance criteria:**
- `analyze_video()` returns a dict with keys: `session_id`, `timestamp`, `observations`, `updated_behaviors`, `confusion_flags`, `session_summary`
- `respond_to_command()` returns a dict with keys: `recognized`, `matched_action_id`, `confidence`, `narration`, `command_transcript`
- Both functions raise a clear exception (not silent failure) if `GEMINI_API_KEY` is unset
- `dog_system.md` is loaded once at module import, not per-call

**Time estimate:** 20 min
**Owner:** Claude Code
**Dependency:** T-001 (google-generativeai must be installed)

### T-004 | Wire Gemini path into main.py cmd_train and cmd_command
**Story:** `cmd_train` should detect Spaces credentials and route to Gemini path or legacy path.
**Logic:**
```
if os.getenv("GEMINI_API_KEY"):
    # use gemini_processor.py directly (no ffmpeg)
else:
    # legacy path: processor.py + agent.py
```
**Note:** The Spaces check described in CLAUDE.md is actually the wrong gate for local Gemini use. The correct gate is `GEMINI_API_KEY` presence. Keep the fallback clean.

**Acceptance criteria:**
- With `GEMINI_API_KEY` set and `ANTHROPIC_API_KEY` unset, `cmd_train` runs via Gemini path
- With only `ANTHROPIC_API_KEY` set, falls back to legacy path
- Both produce identical CLI output (same rich table, same panel)

**Time estimate:** 15 min
**Owner:** Claude Code
**Dependency:** T-003

---

## P1 Tasks — Nice to Have (estimated ~60 min total)

Ship these if P0 is done with time remaining. Listed in priority order.

### T-005 | Write storage.py (DO Spaces integration)
**Story:** Enable syncing behaviors.json to Spaces so state persists across restarts.
**Scope:** Two functions only:
- `download_video(spaces_key) -> local_path` — downloads to a temp file, returns path
- `sync_state_to_spaces(behaviors_path, sessions_path)` — uploads both JSON files to `state/` prefix

**Acceptance criteria:**
- Graceful no-op (log warning, do not crash) when `DO_SPACES_*` env vars are absent
- Uses boto3 with explicit endpoint_url constructed from `DO_SPACES_REGION`
- Called at end of `cmd_train` after `save_behaviors()`, gated on credentials present

**Time estimate:** 15 min
**Owner:** Claude Code
**Dependency:** boto3 installed (T-001 covers this if requirements.txt is updated)

### T-006 | Update requirements.txt
**Story:** requirements.txt currently only lists 4 packages; all integration deps are missing.
**Add:** `google-generativeai>=0.8.0`, `boto3>=1.28.0`, `fastapi>=0.110.0`, `uvicorn>=0.29.0`
**Note on railtracks:** Do NOT add railtracks until T-007 confirms it exists on PyPI. Add a comment placeholder.
**Time estimate:** 5 min (but do this before T-003/T-005/T-008)
**Owner:** Claude Code

### T-007 | Verify railtracks and write pipeline.py
**Story:** Railtracks is listed in the architecture but is an unknown quantity.
**Action:**
1. Run `pip install railtracks` and check if it succeeds
2. If it installs: read its API, implement three-node pipeline as designed
3. If it does not exist on PyPI: implement `pipeline.py` as a simple sequential async runner (three plain async functions chained) — no framework dependency. Document the pivot in `docs/decisions/001-railtracks-fallback.md`

**Acceptance criteria (either path):**
- `from pipeline import run_train_pipeline` is callable
- Takes a Spaces key as input, runs download → Gemini analyze → persist
- Errors in any node propagate cleanly with a descriptive message

**Time estimate:** 20 min
**Owner:** Claude Code
**Dependency:** T-003, T-005

### T-008 | Write webhook.py and wire serve subcommand
**Story:** Enable Nexla-triggered automation demo.
**Scope:**
- `POST /webhook/train` — reads `{"video_key": "..."}` from body, fires `run_train_pipeline` as BackgroundTask
- `GET /health` — returns `{"status": "ok", "behaviors_count": N}`
- `main.py serve` subcommand → `uvicorn.run("webhook:app", host="0.0.0.0", port=8080)`

**Acceptance criteria:**
- `python main.py serve` starts without error
- `curl localhost:8080/health` returns JSON with behaviors count
- A POST to `/webhook/train` with a valid Spaces key triggers the pipeline (or returns 202 Accepted immediately and runs in background)

**Time estimate:** 20 min
**Owner:** Claude Code
**Dependency:** T-007 (pipeline.py must exist)

---

## P2 Tasks — Skip (document and archive)

| Task | Reason to skip |
|---|---|
| Live Nexla webhook integration | Requires Nexla account/config not in our control; webhook endpoint itself is the demo artifact |
| Streaming Gemini responses | Adds complexity, no demo value; dog narration is short enough for blocking calls |
| behaviors.json conflict resolution across concurrent sessions | No concurrent sessions in a hackathon demo |
| Auth/security on webhook endpoints | Hackathon scope; would add 30+ min for zero demo value |
| Unit test suite | Build time not justified given the hours constraint |

---

## Execution Order

Run these in sequence. Each task is a single Claude Code prompt.

```
1. T-006  Update requirements.txt (5 min)
2. T-001  pip install (5 min)
3. T-002  Verify legacy baseline with a test file (10 min)
4. T-003  gemini_processor.py (20 min)
5. T-004  Wire Gemini into main.py (15 min)
         ^^^ DEMO CHECKPOINT — project is fully demo-able here ^^^
6. T-007  Verify railtracks, write pipeline.py (20 min)
7. T-005  storage.py (15 min)
8. T-008  webhook.py + serve subcommand (20 min)
         ^^^ FULL INTEGRATION CHECKPOINT ^^^
```

---

## Blockers and Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| B-001 | railtracks does not exist on PyPI | High | Medium | T-007 explicitly checks first; fallback to plain async runner is pre-decided |
| B-002 | Gemini Files API rejects short/test videos | Medium | High | Test with a real file in T-002 equivalent; Files API has a minimum size; have a fallback test clip ready |
| B-003 | GEMINI_API_KEY not provisioned | Medium | High (blocks T-003) | Confirm key is available before starting T-003; legacy path remains the demo fallback |
| B-004 | DO Spaces credentials not set | Low | Low | T-005 is gated on creds; storage.py gracefully no-ops; not on the critical path |
| B-005 | Gemini JSON output does not match expected schema | Medium | Medium | Add a schema validation wrapper in gemini_processor.py that raises with a diff on mismatch |

---

## Demo Script (for when P0 is done)

```bash
# 1. Train the dog on a session video
python main.py train session1.mp4

# 2. Show what it learned
python main.py show

# 3. Give it a command
python main.py command sit.mp3

# 4. (If P1 complete) Start the webhook server
python main.py serve
# In another terminal:
curl -X POST localhost:8080/webhook/train -H "Content-Type: application/json" \
  -d '{"video_key": "uploads/session2.mp4"}'
curl localhost:8080/health
```

---

## Files to be created by Claude Code

| File | Priority | Notes |
|---|---|---|
| `gemini_processor.py` | P0 | Core Gemini integration |
| `storage.py` | P1 | DO Spaces wrapper |
| `pipeline.py` | P1 | Railtracks or plain async |
| `webhook.py` | P1 | FastAPI server |
| `docs/decisions/001-railtracks-fallback.md` | P1 | Only if railtracks is unavailable |

**Files to be modified:**
| File | Change |
|---|---|
| `requirements.txt` | Add 4 new deps |
| `main.py` | Add Gemini routing in cmd_train/cmd_command + serve subcommand |
