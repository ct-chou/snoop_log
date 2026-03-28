from dotenv import load_dotenv
load_dotenv()

import os
from pathlib import Path

import streamlit as st

from gemini_processor import analyze_video
from log import (
    append_session,
    load_behaviors,
    load_sessions,
    next_session_id,
    save_behaviors,
)

st.set_page_config(page_title="snoop_log", page_icon="🐾", layout="wide")

VIDEOS_DIR    = Path("videos")
DOG_STATES_DIR = Path("dog_states")
VIDEOS_DIR.mkdir(exist_ok=True)

# ── Animated dog GIFs ──────────────────────────────────────────────────────────

STATE_LABELS = {
    "alert":     "👀 On alert — something caught my attention",
    "confident": "💪 I know this one!",
    "happy":     "🎉 Yes! I did the right thing!",
    "confused":  "❓ Wait... what did that mean?",
}


def render_dog(state: str, caption: bool = True) -> None:
    gif_path = DOG_STATES_DIR / f"{state}.gif"
    if not gif_path.exists():
        gif_path = DOG_STATES_DIR / "alert.gif"   # fallback
    st.image(str(gif_path), use_container_width=True)
    if caption:
        st.caption(STATE_LABELS.get(state, ""))


# ── Helpers ────────────────────────────────────────────────────────────────────

def delta_badge(delta_str: str) -> str:
    if delta_str == "new":
        return '<span style="background:#92400e;color:white;padding:2px 8px;border-radius:4px;font-size:0.78em;font-weight:600">new</span>'
    try:
        val = float(delta_str)
    except (ValueError, TypeError):
        return ""
    if val > 0:
        return f'<span style="background:#166534;color:white;padding:2px 8px;border-radius:4px;font-size:0.78em;font-weight:600">{delta_str}</span>'
    elif val < 0:
        return f'<span style="background:#991b1b;color:white;padding:2px 8px;border-radius:4px;font-size:0.78em;font-weight:600">{delta_str}</span>'
    return ""


def dominant_state(session: dict) -> str:
    """Pick the most emotionally significant state from a session's timeline."""
    timeline = session.get("timeline", [])
    if not timeline:
        return "confused" if session.get("confusion_flags") else "confident"
    # Priority: confused > happy > confident > alert
    states = [e.get("state", "alert") for e in timeline]
    for s in ("confused", "happy", "confident", "alert"):
        if s in states:
            return s
    return "alert"


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("images/snooplogclean.PNG", use_container_width=True)
    st.markdown("### Agentic AI Canine Companion")
    st.caption("Powered by Gemini 2.5 Flash")
    st.divider()
    behaviors = load_behaviors()
    sessions  = load_sessions()
    st.metric("Behaviors learned", len(behaviors))
    st.metric("Training sessions", len(sessions))
    if behaviors:
        avg = sum(b["confidence"] for b in behaviors) / len(behaviors)
        st.metric("Avg confidence", f"{avg:.0%}")

# ── Header ─────────────────────────────────────────────────────────────────────

st.image("images/snooplogwithtitle.PNG", width=420)
st.caption("a dog's training journal — powered by Gemini 2.5 Flash")

# ── Success panel after training ───────────────────────────────────────────────

if "last_result" in st.session_state:
    r         = st.session_state.pop("last_result")
    vid_path  = st.session_state.pop("last_video_path", None)
    state     = dominant_state(r)
    timeline  = r.get("timeline", [])

    st.success(f"Session {r['session_id']} complete — {r['session_summary']}")
    st.divider()

    col_vid, col_dog = st.columns([3, 1])
    with col_vid:
        if vid_path and Path(vid_path).exists():
            st.video(vid_path)
        if timeline:
            st.markdown("#### What I was thinking")
            for moment in timeline:
                s      = moment.get("state", "alert")
                emoji  = {"alert": "👀", "confident": "💪", "happy": "🎉", "confused": "❓"}.get(s, "🐾")
                st.markdown(
                    f"`{moment.get('time', '?')}` {emoji} *{moment.get('event', '')}*"
                )
    with col_dog:
        render_dog(state)

    st.divider()

# ── Train ──────────────────────────────────────────────────────────────────────

st.subheader("Train")
st.caption("Upload a training session video. Gemini will watch it from the dog's POV and update the behavior library.")

uploaded = st.file_uploader("Training video", type=["mp4", "mov"])

if uploaded:
    col1, _ = st.columns([1, 4])
    with col1:
        train_btn = st.button("Train", type="primary", use_container_width=True)

    if train_btn:
        saved_path = None
        try:
            session_id = next_session_id()
            suffix     = "." + uploaded.name.rsplit(".", 1)[-1].lower()
            saved_path = str(VIDEOS_DIR / f"session_{session_id}{suffix}")

            with open(saved_path, "wb") as f:
                f.write(uploaded.read())

            current_behaviors = load_behaviors()

            with st.status("Analyzing training session...", expanded=True) as status:
                st.write("Step 1/2 — uploading to Gemini Files API (10–30s)...")
                result = analyze_video(saved_path, current_behaviors, session_id)
                st.write("Step 2/2 — saving results...")
                save_behaviors(result["updated_behaviors"])
                append_session({
                    "session_id":      result["session_id"],
                    "timestamp":       result["timestamp"],
                    "observations":    result["observations"],
                    "session_summary": result["session_summary"],
                    "confusion_flags": result.get("confusion_flags", []),
                    "timeline":        result.get("timeline", []),
                    "video_path":      saved_path,
                })
                status.update(label=f"Session {session_id} complete", state="complete")

            st.session_state["last_result"]     = result
            st.session_state["last_video_path"] = saved_path
            st.rerun()

        except Exception as e:
            st.error(f"Training failed: {e}")

st.divider()

# ── Behavior Dashboard ─────────────────────────────────────────────────────────

st.subheader("Learned Behaviors")

behaviors = load_behaviors()

if not behaviors:
    st.info("No behaviors learned yet. Upload a training video to get started.")
else:
    for b in behaviors:
        confidence = min(1.0, max(0.0, float(b["confidence"])))
        badge      = delta_badge(str(b.get("delta", "")))

        col_main, col_metric = st.columns([4, 1])
        with col_main:
            st.markdown(f"**{b['action_id']}** &nbsp; {badge}", unsafe_allow_html=True)
            st.progress(confidence)
            st.caption(f"Sound: {b.get('trigger_sound', '—')}")
            if b.get("trigger_gesture"):
                st.caption(f"Gesture: {b['trigger_gesture']}")
            if b.get("reward_history"):
                st.caption(f"Rewards: {b['reward_history']}")
        with col_metric:
            st.metric(label="confidence", value=f"{confidence:.0%}")

        st.divider()

# ── Session History ────────────────────────────────────────────────────────────

st.subheader("Session History")

sessions = load_sessions()

if not sessions:
    st.info("No sessions yet.")
else:
    sessions_sorted = sorted(sessions, key=lambda s: s["session_id"], reverse=True)

    for i, s in enumerate(sessions_sorted):
        summary        = s.get("session_summary", "")
        flags          = s.get("confusion_flags", [])
        flag_indicator = f"  ⚠️ {len(flags)}" if flags else ""
        label          = f"Session {s['session_id']} — {summary[:65]}{'...' if len(summary) > 65 else ''}"

        with st.expander(label + flag_indicator, expanded=(i == 0)):
            timeline  = s.get("timeline", [])
            vid_path  = s.get("video_path")
            state     = dominant_state(s)

            col_left, col_right = st.columns([3, 1])

            with col_left:
                if vid_path and Path(vid_path).exists():
                    st.video(vid_path)

                st.write(s.get("observations", ""))
                st.caption(f"Recorded: {s.get('timestamp', '')}")

                if timeline:
                    st.markdown("**Reaction timeline**")
                    for moment in timeline:
                        ms    = moment.get("state", "alert")
                        emoji = {"alert": "👀", "confident": "💪", "happy": "🎉", "confused": "❓"}.get(ms, "🐾")
                        st.markdown(f"`{moment.get('time', '?')}` {emoji} *{moment.get('event', '')}*")

                if flags:
                    for flag in flags:
                        st.warning(flag, icon="⚠️")
                else:
                    st.success("No confusion flags this session", icon="✓")

            with col_right:
                render_dog(state)
