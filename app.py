from dotenv import load_dotenv
load_dotenv()  # must come before gemini_processor import

import os
import tempfile
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

# ── Header ─────────────────────────────────────────────────────────────────────

st.title("🐾 snoop_log")
st.caption("a dog's training journal — powered by Gemini 2.5 Flash")

# ── Success toast after training ───────────────────────────────────────────────

if "last_result" in st.session_state:
    r = st.session_state.pop("last_result")
    st.success(f"Session {r['session_id']} complete — {r['session_summary']}")

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
        tmp_path = None
        try:
            suffix = "." + uploaded.name.rsplit(".", 1)[-1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name

            current_behaviors = load_behaviors()
            session_id = next_session_id()

            with st.status("Analyzing training session...", expanded=True) as status:
                st.write(f"Step 1/2 — uploading video to Gemini Files API (10–30s)")
                result = analyze_video(tmp_path, current_behaviors, session_id)
                st.write("Step 2/2 — saving results")
                save_behaviors(result["updated_behaviors"])
                append_session({
                    "session_id": result["session_id"],
                    "timestamp": result["timestamp"],
                    "observations": result["observations"],
                    "session_summary": result["session_summary"],
                    "confusion_flags": result.get("confusion_flags", []),
                })
                status.update(label=f"Session {session_id} complete", state="complete")

            st.session_state["last_result"] = result
            st.rerun()

        except Exception as e:
            st.error(f"Training failed: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

st.divider()

# ── Behavior Dashboard ─────────────────────────────────────────────────────────

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


st.subheader("Learned Behaviors")

behaviors = load_behaviors()

if not behaviors:
    st.info("No behaviors learned yet. Upload a training video to get started.")
else:
    for b in behaviors:
        confidence = min(1.0, max(0.0, float(b["confidence"])))
        badge = delta_badge(str(b.get("delta", "")))

        col_main, col_metric = st.columns([4, 1])
        with col_main:
            st.markdown(
                f"**{b['action_id']}** &nbsp; {badge}",
                unsafe_allow_html=True,
            )
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
        summary = s.get("session_summary", "")
        label = f"Session {s['session_id']} — {summary[:70]}{'...' if len(summary) > 70 else ''}"
        flags = s.get("confusion_flags", [])
        flag_indicator = f"  ⚠️ {len(flags)}" if flags else ""

        with st.expander(label + flag_indicator, expanded=(i == 0)):
            st.write(s.get("observations", ""))
            st.caption(f"Recorded: {s.get('timestamp', '')}")

            if flags:
                for flag in flags:
                    st.warning(flag, icon="⚠️")
            else:
                st.success("No confusion flags this session", icon="✓")
