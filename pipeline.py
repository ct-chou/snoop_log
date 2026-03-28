"""
pipeline.py — Railtracks orchestration for the snoop_log training pipeline.

Replaces the imperative code in cmd_train with three sequential nodes:

  node_download_video  (no-op locally, downloads from Spaces if key present)
       ↓
  node_gemini_analyze  (upload to Gemini Files API, analyze, return result dict)
       ↓
  node_persist_results (save behaviors + session, sync to Spaces if available)

Entry point:
    flow = rt.Flow("snoop_log_train", entry_point=node_download_video)
    result = flow.invoke(video_path, session_id, current_behaviors)
"""

import os
from pathlib import Path

import railtracks as rt

from gemini_processor import analyze_video
from log import append_session, load_behaviors, next_session_id, save_behaviors


# ── Node 1: Download / resolve video ──────────────────────────────────────────

@rt.function_node
async def node_download_video(video_path: str, session_id: int) -> dict:
    """
    Resolve the video path. If DO Spaces credentials are present and the path
    looks like an object key (no local file), download from Spaces first.
    Returns a dict with resolved local path and session_id.
    """
    path = Path(video_path)

    if not path.exists():
        # Try Spaces download if credentials available
        spaces_key    = os.environ.get("DO_SPACES_KEY")
        spaces_secret = os.environ.get("DO_SPACES_SECRET")
        spaces_bucket = os.environ.get("DO_SPACES_BUCKET")
        spaces_region = os.environ.get("DO_SPACES_REGION", "nyc3")

        if spaces_key and spaces_secret and spaces_bucket:
            import boto3
            s3 = boto3.client(
                "s3",
                region_name=spaces_region,
                endpoint_url=f"https://{spaces_region}.digitaloceanspaces.com",
                aws_access_key_id=spaces_key,
                aws_secret_access_key=spaces_secret,
            )
            local = Path(f"/tmp/{path.name}")
            s3.download_file(spaces_bucket, video_path, str(local))
            video_path = str(local)
        else:
            raise FileNotFoundError(
                f"Video not found locally and no Spaces credentials set: {video_path}"
            )

    return {"video_path": video_path, "session_id": session_id}


# ── Node 2: Gemini analysis ────────────────────────────────────────────────────

@rt.function_node
async def node_gemini_analyze(video_path: str, session_id: int) -> dict:
    """
    Upload the video to Gemini Files API and run dog-POV analysis.
    Returns the full result dict (observations, updated_behaviors, timeline, etc.).
    """
    current_behaviors = load_behaviors()
    result = analyze_video(video_path, current_behaviors, session_id)
    result["_video_path"] = video_path   # carry forward for persist node
    return result


# ── Node 3: Persist results ────────────────────────────────────────────────────

@rt.function_node
async def node_persist_results(result: dict) -> dict:
    """
    Save updated behaviors and session log locally.
    If DO Spaces credentials are present, also sync state files to Spaces.
    Returns the result dict unchanged (for downstream use).
    """
    save_behaviors(result["updated_behaviors"])
    append_session({
        "session_id":      result["session_id"],
        "timestamp":       result["timestamp"],
        "observations":    result["observations"],
        "session_summary": result["session_summary"],
        "confusion_flags": result.get("confusion_flags", []),
        "timeline":        result.get("timeline", []),
        "video_path":      result.get("_video_path", ""),
    })

    # Optional: sync to Spaces
    spaces_key    = os.environ.get("DO_SPACES_KEY")
    spaces_secret = os.environ.get("DO_SPACES_SECRET")
    spaces_bucket = os.environ.get("DO_SPACES_BUCKET")
    spaces_region = os.environ.get("DO_SPACES_REGION", "nyc3")

    if spaces_key and spaces_secret and spaces_bucket:
        import boto3
        s3 = boto3.client(
            "s3",
            region_name=spaces_region,
            endpoint_url=f"https://{spaces_region}.digitaloceanspaces.com",
            aws_access_key_id=spaces_key,
            aws_secret_access_key=spaces_secret,
        )
        for local_path, key in [
            ("behaviors.json", "state/behaviors.json"),
            ("sessions.json",  "state/sessions.json"),
        ]:
            if Path(local_path).exists():
                s3.upload_file(local_path, spaces_bucket, key)

    return result


# ── Flow definition ────────────────────────────────────────────────────────────

async def _train_entrypoint(video_path: str, session_id: int) -> dict:
    """Sequential pipeline: download → analyze → persist."""
    download_result = await rt.call(node_download_video, video_path, session_id)
    analyze_result  = await rt.call(node_gemini_analyze,
                                    download_result["video_path"],
                                    download_result["session_id"])
    final_result    = await rt.call(node_persist_results, analyze_result)
    return final_result


flow = rt.Flow(
    name="snoop_log_train",
    entry_point=_train_entrypoint,
    end_on_error=True,
)


def run_pipeline(video_path: str, session_id: int | None = None) -> dict:
    """
    Synchronous wrapper — call this from cmd_train or the webhook.
    Returns the full result dict from Gemini analysis.
    """
    if session_id is None:
        session_id = next_session_id()
    return flow.invoke(video_path, session_id)
