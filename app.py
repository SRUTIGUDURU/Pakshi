"""
Pakshi - Full Streamlit App
============================
Buyer side  : describe your saree in natural language -> agent finds swatches -> confirm order
Weaver side : see incoming orders -> accept/decline -> upload progress photo

Run with:
    pip install streamlit chromadb scikit-learn openai-whisper gtts
    streamlit run app.py

All backend files must live in the same directory:
    intent_parser.py, agent.py, retrieval.py, setup_chromadb.py,
    fabric_ontology.json, fabric_swatches.json, weaver_profiles.json
"""

import json
import os
import time
import random
import tempfile
import base64
import wave
import struct
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Page config -- must be the very first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Pakshi",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Brand CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg-deep:        #19031c;
    --bg-surface:     #52104c;
    --bg-card:        #8a1c7c;
    --bg-input:       #6a1460;
    --accent-primary: #da4167;
    --accent-hover:   #b22f72;
    --accent-subtle:  #e57f9e;
    --text-primary:   #f0bcd4;
    --text-muted:     #bdada6;
    --text-white:     #ffffff;
    --text-dark:      #19031c;
    --earth:          #899d78;
    --success:        #22c55e;
    --danger:         #ef4444;
    --border:         rgba(240,188,212,0.12);
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: var(--bg-deep);
    color: var(--text-primary);
}
.main { background-color: var(--bg-deep); }
.block-container { padding: 1.5rem 2rem 3rem; max-width: 1100px; }
#MainMenu, footer, header { visibility: hidden; }

.pakshi-wordmark {
    font-size: 2rem;
    font-weight: 800;
    color: var(--text-white);
    letter-spacing: -0.5px;
}
.pakshi-wordmark span { color: var(--accent-primary); }

.tagline {
    font-size: 0.85rem;
    color: var(--text-muted);
    margin-top: -4px;
    margin-bottom: 1.5rem;
}

.card {
    background: rgba(58,24,112,0.6);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    color: var(--text-primary);
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}
.card-highlight {
    background: rgba(58,24,112,0.6);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1.5px solid var(--accent-primary);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    transition: transform 0.18s ease;
}
.card-highlight:hover { transform: translateY(-2px); }

.swatch-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem;
    height: 100%;
}
.swatch-price {
    font-size: 1.4rem;
    font-weight: 800;
    color: var(--accent-primary);
}
.swatch-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.swatch-value {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--text-white);
}
.tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    background: rgba(218,65,103,0.15);
    color: var(--accent-primary);
    font-size: 0.72rem;
    font-weight: 500;
    margin: 2px 2px 0 0;
}

.bubble-agent {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 12px 12px 12px 2px;
    padding: 0.75rem 1rem;
    margin: 0.4rem 0;
    max-width: 82%;
    font-size: 0.9rem;
    line-height: 1.55;
    white-space: pre-wrap;
    color: var(--text-primary);
}
.bubble-user {
    background: var(--bg-card);
    border-radius: 12px 12px 2px 12px;
    padding: 0.75rem 1rem;
    margin: 0.4rem 0 0.4rem auto;
    max-width: 70%;
    font-size: 0.9rem;
    line-height: 1.55;
    text-align: right;
    color: var(--text-white);
}

.state-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.6rem;
}
.state-active  { background: rgba(34,197,94,0.2);  color: #22c55e; }
.state-pending { background: rgba(218,65,103,0.2); color: var(--accent-primary); }
.state-done    { background: rgba(139,28,124,0.4); color: var(--text-muted); }

.section-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--accent-primary);
    margin-bottom: 0.4rem;
}

.confirmed-banner {
    background: linear-gradient(135deg,rgba(34,197,94,0.13),rgba(34,197,94,0.04));
    border: 1.5px solid #22c55e;
    border-radius: 12px;
    padding: 1.4rem;
    text-align: center;
    margin-top: 1rem;
}
.confirmed-banner h2 { color: #22c55e; margin: 0; font-size: 1.5rem; }

.order-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
}
.order-card.accepted { border-color: rgba(34,197,94,0.3); }
.order-card.declined { border-color: rgba(239,68,68,0.3); opacity: 0.6; }

.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background-color: var(--bg-surface) !important;
    color: var(--text-white) !important;
    border: 1.5px solid var(--bg-card) !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 1rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent-primary) !important;
    box-shadow: 0 0 0 2px rgba(218,65,103,0.25) !important;
}

.stButton > button {
    background: var(--accent-primary) !important;
    color: var(--text-white) !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.5rem 1.4rem !important;
    font-family: 'Inter', sans-serif !important;
    transition: opacity 0.15s;
}
.stButton > button:hover {
    opacity: 0.88 !important;
    box-shadow: 0 0 16px rgba(218,65,103,0.4) !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    color: var(--text-muted) !important;
    border: 1.5px solid var(--bg-card) !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: var(--accent-primary) !important;
    color: var(--text-white) !important;
}

.pakshi-divider {
    height: 1px;
    background: var(--border);
    margin: 1.2rem 0;
}

.reasoning-box {
    background: rgba(218,65,103,0.08);
    border-left: 3px solid var(--accent-primary);
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    font-size: 0.82rem;
    color: var(--text-muted);
    font-style: italic;
    line-height: 1.6;
    margin: 0.6rem 0;
}

.step-row {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 0.3rem 0;
    font-size: 0.85rem;
}
.step-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}
.step-dot.done    { background: #22c55e; }
.step-dot.active  { background: var(--accent-primary); }
.step-dot.pending { background: var(--bg-card); opacity: 0.4; }

.stRadio > div { gap: 0.4rem; }
.stRadio label { font-size: 0.88rem !important; color: var(--text-primary) !important; }

.stSelectbox > div > div {
    background-color: var(--bg-surface) !important;
    color: var(--text-white) !important;
    border: 1.5px solid var(--bg-card) !important;
    border-radius: 8px !important;
}

.streamlit-expanderHeader {
    color: var(--accent-primary) !important;
    font-weight: 600 !important;
}
.streamlit-expanderContent {
    background: var(--bg-surface) !important;
    color: var(--text-primary) !important;
    border-radius: 0 0 8px 8px !important;
}

.stAlert {
    background-color: var(--bg-surface) !important;
    border-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
}
.stSuccess {
    background-color: rgba(34,197,94,0.1) !important;
    border-color: #22c55e !important;
    color: #22c55e !important;
}
.stInfo {
    background-color: rgba(218,65,103,0.08) !important;
    border-color: var(--accent-primary) !important;
    color: var(--text-primary) !important;
}
.stWarning {
    background-color: rgba(218,65,103,0.08) !important;
    border-color: var(--accent-primary) !important;
    color: var(--accent-primary) !important;
}
.stError {
    background-color: rgba(239,68,68,0.1) !important;
    border-color: #ef4444 !important;
    color: #ef4444 !important;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Audio Validation Function (Fixes the "reshape" error)
# ---------------------------------------------------------------------------
def _audio_contains_sound(file_path: str, threshold: int = 100) -> bool:
    """
    Validates that the WAV file contains actual audio (non-zero amplitude).
    Returns True if sound is detected, False if it's pure silence or corrupted.
    This completely eliminates the "cannot reshape tensor of 0 elements" error.
    """
    try:
        with wave.open(file_path, 'rb') as wf:
            n_frames = wf.getnframes()
            if n_frames < 100:  # Too short to contain speech
                return False
            
            # Read up to 2000 frames (enough to detect any sound)
            read_frames = min(n_frames, 2000)
            raw_data = wf.readframes(read_frames)
            
            if len(raw_data) < 100:
                return False
            
            # Check if any sample has amplitude above threshold
            sample_count = min(read_frames, 500)
            for i in range(0, sample_count * 2, 2):
                val = struct.unpack('<h', raw_data[i:i+2])[0]
                if abs(val) > threshold:
                    return True
            
            return False
            
    except Exception:
        return False


def _fix_wav_header(file_path: str) -> bool:
    """
    Attempts to fix a corrupted WAV header by rewriting it using pydub.
    Returns True if the fix succeeded and the file contains sound.
    """
    try:
        from pydub import AudioSegment
        
        # Try loading the file with pydub (which uses ffmpeg to parse corrupt headers)
        audio = AudioSegment.from_file(file_path)
        
        # Check if there's any audio data
        if len(audio) < 200:  # Less than 200ms = likely silence
            return False
        
        # Export as a clean WAV
        audio.export(file_path, format="wav")
        
        # Verify it now has sound
        return _audio_contains_sound(file_path)
        
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Backend loader (cached; gracefully degrades if backend missing)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _load_agent_class():
    try:
        from agent import PakshiAgent
        return PakshiAgent, None
    except Exception as exc:
        return None, str(exc)


@st.cache_data(show_spinner=False)
def _load_weaver_profiles():
    try:
        p = Path(__file__).parent / "weaver_profiles.json"
        with open(p, encoding="utf-8") as f:
            return json.load(f)["weaver_profiles"]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Whisper loader (cached)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _load_whisper_model():
    try:
        import whisper
        # Use "base" for speed, "small" for accuracy. "base" is faster.
        return whisper.load_model("base"), None
    except Exception as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# TTS helper
# ---------------------------------------------------------------------------
def _tts_bytes(text: str, lang: str = "hi") -> bytes | None:
    if not text:
        return None
    spoken = ". ".join(text.split(". ")[:2]).strip()
    try:
        from gtts import gTTS
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp_path = tmp.name
        gTTS(text=spoken, lang=lang, slow=False).save(tmp_path)
        with open(tmp_path, "rb") as f:
            data = f.read()
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return data
    except Exception:
        return None


def _autoplay_audio(audio_bytes: bytes, fmt: str = "mp3") -> None:
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(
        f'<audio autoplay style="display:none">'
        f'<source src="data:audio/{fmt};base64,{b64}" type="audio/{fmt}">'
        f'</audio>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Audio processing — fixed and robust
# ---------------------------------------------------------------------------
_WHISPER_OPTIONS = {
    "beam_size": 3,                      # Faster than 5, still accurate
    "temperature": (0.0, 0.2, 0.4),      # Fewer retries = faster
    "compression_ratio_threshold": 2.4,
    "no_speech_threshold": 0.6,
    "condition_on_previous_text": False,
    "word_timestamps": False,
    "fp16": False,
}
_WHISPER_LANGUAGE = None


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
def _init_buyer_state() -> None:
    defaults: dict = {
        "agent":           None,
        "history":         [],
        "current_state":   "greeting",
        "swatches":        [],
        "selected_swatch": None,
        "order":           None,
        "agent_data":      {},
        "awaiting":        None,
        "reasoning_log":   [],
        "one_of_a_kind":   [],
        "buyer_orders":    [],
        "agent_thinking":  False,
        "last_audio_hash": None,   # Tracks the last audio hash to prevent re-processing
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _init_weaver_state() -> None:
    if "weaver_orders" not in st.session_state:
        st.session_state["weaver_orders"] = _make_demo_orders()
    if "weaver_id" not in st.session_state:
        st.session_state["weaver_id"] = "W001"


def _make_demo_orders() -> list[dict]:
    return [
        {
            "order_id":   "PKS-2847",
            "fabric":     "Cotton-Silk",
            "weave_style":"Pochampally Ikat",
            "color":      "Teal with gold border",
            "occasion":   "Summer Wedding",
            "buyer_feel": "flowy, breathable yet elegant",
            "price":      1800,
            "delivery_by":"July 26, 2026",
            "status":     "pending",
            "photo":      None,
            "buyer_note": "Light saree, summer wedding, Rs.1500 - agent proposed Cotton-Silk at Rs.1800",
        },
        {
            "order_id":   "PKS-2831",
            "fabric":     "Cotton",
            "weave_style":"Pochampally Ikat",
            "color":      "Navy blue",
            "occasion":   "Office / Daily Wear",
            "buyer_feel": "breathable, cool, non-itchy",
            "price":      750,
            "delivery_by":"July 20, 2026",
            "status":     "accepted",
            "photo":      None,
            "buyer_note": "Office wear, breathable cotton under Rs.800",
        },
        {
            "order_id":   "PKS-2819",
            "fabric":     "Silk",
            "weave_style":"Pochampally Ikat",
            "color":      "Deep red with zari",
            "occasion":   "Wedding Reception",
            "buyer_feel": "royal, heavy, grand",
            "price":      4200,
            "delivery_by":"August 2, 2026",
            "status":     "pending",
            "photo":      None,
            "buyer_note": "Sister's wedding reception, deep red silk, grand",
        },
    ]


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
def _render_header() -> None:
    c1, _ = st.columns([1, 3])
    with c1:
        st.markdown(
            '<div class="pakshi-wordmark">Pakshi</div>'
            '<div class="tagline">Turning buyer intent into artisan opportunity</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Step indicator
# ---------------------------------------------------------------------------
STATE_STEPS = [
    ("greeting",         "Start"),
    ("collecting",       "Intent"),
    ("retrieved",        "Swatches"),
    ("fallback_pending", "Fallback"),
    ("swatch_selected",  "Locked"),
    ("broadcasting",     "Broadcast"),
    ("weaver_selected",  "Matched"),
    ("confirmed",        "Confirmed"),
]
_HIDDEN_STATES = {"fallback_pending", "broadcasting", "weaver_selected"}


def _step_indicator(current: str) -> None:
    active_idx = next((i for i, (k, _) in enumerate(STATE_STEPS) if k == current), 0)
    parts = ['<div style="display:flex;gap:1.2rem;align-items:center;'
             'margin-bottom:1rem;flex-wrap:wrap;">']
    for i, (key, label) in enumerate(STATE_STEPS):
        if key in _HIDDEN_STATES:
            continue
        if i < active_idx:
            dot_cls, color = "done",    "#22c55e"
        elif i == active_idx:
            dot_cls, color = "active",  "var(--accent-primary)"
        else:
            dot_cls, color = "pending", "var(--text-muted)"
        parts.append(
            f'<div class="step-row">'
            f'<div class="step-dot {dot_cls}"></div>'
            f'<span style="font-size:0.78rem;color:{color};font-weight:500;">{label}</span>'
            f'</div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Swatch card renderer
# ---------------------------------------------------------------------------
def _render_swatch_card(swatch: dict) -> None:
    tags_html = "".join(
        f'<span class="tag">{t}</span>'
        for t in swatch.get("sensory_tags", [])[:3]
    )
    st.markdown(f"""
    <div class="swatch-card">
        <div style="font-weight:700;font-size:0.95rem;margin-bottom:2px;
                    color:var(--text-white);">
            {swatch.get("weave_style", "—")}
        </div>
        <div style="font-size:0.82rem;color:var(--text-muted);margin-bottom:8px;">
            {swatch.get("color", "—")}
        </div>
        <div class="swatch-price">Rs.{swatch.get("price_inr", "?")}</div>
        <div style="margin:8px 0">{tags_html}</div>
        <div class="pakshi-divider"></div>
        <div class="swatch-label">Weaver</div>
        <div class="swatch-value">{swatch.get("weaver_name", "—")}</div>
        <div style="font-size:0.78rem;color:var(--text-muted);">
            {swatch.get("weaver_cluster", "")}, {swatch.get("weaver_state", "")}
        </div>
        <div style="margin-top:4px;font-size:0.82rem;color:var(--text-primary);">
            Rating: {swatch.get("weaver_rating", "?")} &nbsp;·&nbsp;
            {swatch.get("delivery_days", "?")} days
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Core message dispatcher
# ---------------------------------------------------------------------------
def _send_message(user_text: str) -> None:
    user_text = (user_text or "").strip()
    if not user_text:
        return

    PakshiAgent, err = _load_agent_class()
    if err or PakshiAgent is None:
        st.error(f"Backend could not be loaded: {err}")
        return

    if st.session_state.get("agent") is None:
        try:
            st.session_state["agent"] = PakshiAgent()
        except Exception as exc:
            st.error(f"Agent initialisation failed: {exc}")
            return

    agent = st.session_state["agent"]
    st.session_state["history"].append(("user", user_text))
    st.session_state["agent_thinking"] = True

    try:
        response = agent.chat(user_text)
    except Exception as exc:
        st.session_state["agent_thinking"] = False
        st.session_state["history"].append(
            ("agent", f"Something went wrong: {exc}. Please try again.")
        )
        return

    st.session_state["agent_thinking"] = False

    msg   = response.get("message", "")
    state = response.get("state",   "greeting")
    data  = response.get("data",    {})

    st.session_state["current_state"] = state
    st.session_state["history"].append(("agent", msg))
    st.session_state["agent_data"]    = data

    if data.get("swatches"):
        st.session_state["swatches"] = data["swatches"]

    if data.get("order"):
        st.session_state["order"] = data["order"]

    if state == "confirmed" and data.get("order"):
        raw = data["order"]
        sw  = raw.get("selected_swatch") or {}
        wv  = raw.get("selected_weaver")  or {}
        tracked = {
            "order_id":    raw.get("order_id",    "PKS-???"),
            "weave_style": sw.get("weave_style",  "—"),
            "color":       sw.get("color",         "—"),
            "price":       sw.get("price_inr",     0),
            "weaver_name": wv.get("weaver_name",  "—"),
            "status":      "In Production",
            "photo_path":  None,
            "intent":      user_text,
        }
        existing_ids = {o["order_id"] for o in st.session_state.get("buyer_orders", [])}
        if tracked["order_id"] not in existing_ids:
            st.session_state["buyer_orders"].append(tracked)

    if state in ("fallback_pending", "broadcasting", "weaver_selected", "confirmed"):
        snippet = msg[:120] + ("..." if len(msg) > 120 else "")
        st.session_state["reasoning_log"].append(f"[{state.upper()}] {snippet}")


# ---------------------------------------------------------------------------
# BUYER PAGE
# ---------------------------------------------------------------------------
def _buyer_page() -> None:
    _init_buyer_state()

    st.markdown('<div class="section-label">Buyer</div>', unsafe_allow_html=True)

    with st.expander("How to use this app (Buyer)"):
        st.markdown("""
**Step 1 — Speak or type your request.**
Describe what you want in your own words and language,
for example: *"Light saree for summer wedding, Rs.1500, mint green."*

**Step 2 — Review swatches.**
The agent shows up to 3 matching handloom swatches with fabric, weave style,
colour, price, weaver name, and delivery estimate.

**Step 3 — Select a swatch.**
Type 1, 2, or 3 — or click the Select button — to lock your choice.

**Step 4 — Confirm the order.**
Click Confirm Order. The agent autonomously picks the best available weaver
based on proximity and delivery history. Your order is placed on Meesho.

**Step 5 — Reject if needed.**
If the finished piece does not meet your expectation, click Reject Piece.
It moves to the One of a Kind resale tab at a wholesale price. No waste, no loss.
        """)

    if st.session_state.get("agent_thinking"):
        st.markdown(
            '<div style="background:rgba(218,65,103,0.12);border-left:3px solid var(--accent-primary);'
            'padding:0.6rem 1rem;border-radius:0 8px 8px 0;font-size:0.85rem;'
            'color:var(--accent-primary);margin-bottom:0.8rem;">'
            'Agent is reasoning through fabric options...</div>',
            unsafe_allow_html=True,
        )

    buyer_orders = st.session_state.get("buyer_orders", [])
    if buyer_orders:
        with st.expander(f"Your Orders ({len(buyer_orders)})"):
            for bo in buyer_orders:
                status = bo.get("status", "In Production")
                status_color = {
                    "In Production":  "var(--accent-primary)",
                    "Photo Available": "var(--bg-card)",
                    "Completed":       "#22c55e",
                }.get(status, "var(--text-muted)")
                photo_note = (
                    '<div style="font-size:0.78rem;color:#22c55e;margin-top:4px;">'
                    'Progress photo received from weaver</div>'
                    if bo.get("photo_path") else ""
                )
                st.markdown(f"""
                <div style="background:rgba(58,24,112,0.6);border:1px solid var(--border);
                    border-radius:10px;padding:0.8rem 1rem;margin-bottom:0.5rem;">
                    <div style="display:flex;justify-content:space-between;
                        align-items:center;flex-wrap:wrap;gap:0.5rem;">
                        <div>
                            <div style="font-weight:700;font-size:0.9rem;color:var(--text-white);">
                                {bo["weave_style"]} &middot; {bo["color"]}
                            </div>
                            <div style="font-size:0.75rem;color:var(--text-muted);">
                                #{bo["order_id"]} &middot; {bo["weaver_name"]} &middot; Rs.{bo["price"]:,}
                            </div>
                            {photo_note}
                        </div>
                        <div style="background:rgba(0,0,0,0.3);padding:3px 10px;
                            border-radius:999px;font-size:0.72rem;font-weight:700;
                            color:{status_color};">
                            {status}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(
                    f"Re-order {bo['order_id']}",
                    key=f"reorder_{bo['order_id']}",
                ):
                    _send_message(f"{bo['weave_style']}, {bo['color']}, Rs.{bo['price']}")
                    st.rerun()

    _step_indicator(st.session_state["current_state"])

    col_chat, col_panel = st.columns([3, 2], gap="large")

    with col_panel:
        swatches = st.session_state["swatches"]
        if swatches:
            st.markdown(
                '<div class="section-label">Matching Swatches</div>',
                unsafe_allow_html=True,
            )
            for i, sw in enumerate(swatches[:3]):
                _render_swatch_card(sw)
                if st.session_state["current_state"] == "retrieved":
                    if st.button(f"Select Swatch {i + 1}", key=f"sel_{i}"):
                        _send_message(str(i + 1))
                        st.rerun()

        order = st.session_state["order"]
        if order and st.session_state["current_state"] == "confirmed":
            sw = order.get("selected_swatch") or {}
            wv = order.get("selected_weaver")  or {}
            st.markdown(f"""
            <div class="confirmed-banner">
                <h2>Order Confirmed</h2>
                <div style="font-size:0.82rem;color:#86efac;margin-top:4px;">
                    #{order.get("order_id", "—")}
                </div>
                <div style="margin-top:12px;text-align:left;">
                    <div class="swatch-label">Fabric</div>
                    <div class="swatch-value">
                        {sw.get("weave_style", "—")} · {sw.get("color", "—")}
                    </div>
                    <div class="swatch-price" style="margin:6px 0;">
                        Rs.{sw.get("price_inr", "?")}
                    </div>
                    <div class="pakshi-divider"></div>
                    <div class="swatch-label">Weaver (agent-selected)</div>
                    <div class="swatch-value">{wv.get("weaver_name", "—")}</div>
                    <div style="font-size:0.78rem;color:var(--text-muted);">
                        {wv.get("weaver_cluster", "")}, {wv.get("weaver_state", "")} ·
                        Rating: {wv.get("weaver_rating", "?")} ·
                        {wv.get("delivery_days", "?")} days
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="pakshi-divider"></div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="section-label">Not satisfied? Reject this piece.</div>',
                unsafe_allow_html=True,
            )
            st.caption(
                "If the final product does not meet your expectation, move it to "
                "'One of a Kind' resale. The weaver recovers partial value, "
                "you owe nothing, and a unique piece finds a new buyer."
            )
            if st.button("Reject Piece — Move to One of a Kind", use_container_width=True):
                current_order = st.session_state.get("order") or {}
                swatch  = current_order.get("selected_swatch") or {}
                weaver  = current_order.get("selected_weaver")  or {}
                orig    = swatch.get("price_inr", 0)
                resale  = int(orig * 0.6)
                rejected = {
                    "order_id":       current_order.get("order_id", "PKS-XXXX"),
                    "weave_style":    swatch.get("weave_style",  "Unknown"),
                    "color":          swatch.get("color",         "Unknown"),
                    "original_price": orig,
                    "resale_price":   resale,
                    "weaver_name":    weaver.get("weaver_name",  "Unknown"),
                    "weaver_cluster": weaver.get("weaver_cluster","Unknown"),
                    "weaver_state":   weaver.get("weaver_state",  "Unknown"),
                    "sensory_tags":   swatch.get("sensory_tags",  []),
                    "reason":         "Weaving imperfection / colour mismatch",
                }
                st.session_state.setdefault("one_of_a_kind", []).append(rejected)
                for key in ("current_state","order","swatches","history",
                            "agent","reasoning_log","agent_data","awaiting",
                            "selected_swatch","agent_thinking"):
                    st.session_state[key] = (
                        [] if key in ("swatches","history","reasoning_log") else
                        {} if key == "agent_data" else
                        False if key == "agent_thinking" else
                        None if key in ("order","agent","awaiting","selected_swatch") else
                        "greeting"
                    )
                st.success(
                    f"Piece moved to One of a Kind at Rs.{resale:,}. "
                    "Starting a fresh search for you."
                )
                st.rerun()

        if st.session_state["reasoning_log"]:
            st.markdown(
                '<div class="section-label" style="margin-top:1rem;">Agent Reasoning</div>',
                unsafe_allow_html=True,
            )
            for line in st.session_state["reasoning_log"][-3:]:
                st.markdown(
                    f'<div class="reasoning-box">{line}</div>',
                    unsafe_allow_html=True,
                )

    with col_chat:
        for role, text in st.session_state["history"]:
            bubble_cls = "bubble-agent" if role == "agent" else "bubble-user"
            st.markdown(
                f'<div class="{bubble_cls}">{text}</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
        cur = st.session_state["current_state"]

        if cur == "fallback_pending":
            st.markdown(
                '<div class="section-label">Agent is proposing an alternative</div>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Yes, show alternatives", use_container_width=True):
                    _send_message("yes")
                    st.rerun()
            with c2:
                if st.button("No, wait for my budget", use_container_width=True):
                    _send_message("no")
                    st.rerun()

        elif cur == "swatch_selected":
            st.markdown(
                '<div class="section-label">Swatch locked — ready to place order?</div>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Confirm Order", use_container_width=True):
                    _send_message("confirm")
                    st.rerun()
            with c2:
                if st.button("Change Selection", use_container_width=True):
                    _send_message("back")
                    st.rerun()

        elif cur in ("confirmed", "failed"):
            if st.button("Start New Search"):
                ooak   = st.session_state.get("one_of_a_kind", [])
                bords  = st.session_state.get("buyer_orders",  [])
                loaded = st.session_state.get("app_loaded",    False)
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.session_state["one_of_a_kind"] = ooak
                st.session_state["buyer_orders"]  = bords
                st.session_state["app_loaded"]    = loaded
                st.rerun()

        else:
            if cur == "greeting" and not st.session_state["history"]:
                _send_message("hi")
                st.rerun()

            # --- FIXED AUDIO INPUT (Static Key + Hash Tracking) ---
            st.markdown(
                '<div class="section-label">Speak your request</div>',
                unsafe_allow_html=True,
            )

            # Static key ensures the widget doesn't reset on reruns
            audio_file = st.audio_input(
                "Record your fabric request (speak clearly for 2-3 seconds)",
                label_visibility="collapsed",
                key="audio_input_main",
            )

            if audio_file is not None:
                # Generate a unique hash for this audio file
                audio_hash = hash(bytes(audio_file.getbuffer()))
                
                # Only process if this is a NEW audio recording (not the same as before)
                if st.session_state.get("last_audio_hash") != audio_hash:
                    st.session_state["last_audio_hash"] = audio_hash

                    whisper_model, whisper_err = _load_whisper_model()
                    if whisper_err or whisper_model is None:
                        st.warning(
                            f"Voice transcription unavailable ({whisper_err}). "
                            "Please type your request below."
                        )
                        st.session_state["last_audio_hash"] = None
                    else:
                        with st.spinner("Transcribing..."):
                            tmp_path = None
                            try:
                                with tempfile.NamedTemporaryFile(
                                    delete=False, suffix=".wav"
                                ) as tmp:
                                    tmp.write(audio_file.getbuffer())
                                    tmp_path = tmp.name

                                # --- Audio validation removed ---
                                # Pratilekha/Whisper handles silence internally.
                                # The custom validator caused false negatives on Streamlit Cloud.

                                # --- Call model ---
                                result = whisper_model.transcribe(
                                    tmp_path,
                                    language=_WHISPER_LANGUAGE,
                                    **_WHISPER_OPTIONS,
                                )
                                transcribed = (result.get("text") or "").strip()

                                if transcribed and len(transcribed) > 2:
                                    # Check for hallucination
                                    if transcribed.lower() in {"thank you", "thanks", "bye", "hello", "hi", "ok"}:
                                        st.warning(
                                            f'Transcribed: "{transcribed}" — this seems too short or unclear. '
                                            "Please try again or type your request."
                                        )
                                        st.session_state["last_audio_hash"] = None
                                        st.rerun()
                                        return
                                    
                                    st.success(f"Heard: {transcribed}")
                                    _send_message(transcribed)
                                    st.session_state["last_audio_hash"] = None
                                    st.rerun()
                                else:
                                    st.warning(
                                        "Could not detect clear speech. "
                                        "Please try again or type below."
                                    )
                                    st.session_state["last_audio_hash"] = None
                                    st.rerun()

                            except Exception as exc:
                                err_msg = str(exc)
                                if "reshape" in err_msg:
                                    st.warning(
                                        "🔇 The recording was silent or corrupted. "
                                        "Please try speaking clearly for 2-3 seconds, or type your request below."
                                    )
                                else:
                                    st.error(
                                        f"Transcription error: {err_msg}. "
                                        "Please type your request below."
                                    )
                                st.session_state["last_audio_hash"] = None
                                st.rerun()
                            finally:
                                if tmp_path and os.path.exists(tmp_path):
                                    try:
                                        os.unlink(tmp_path)
                                    except OSError:
                                        pass

            st.markdown(
                '<div class="section-label" style="margin-top:0.8rem;">Or type</div>',
                unsafe_allow_html=True,
            )

            placeholder_map = {
                "collecting": "e.g. Light saree for summer wedding, Rs.1500, mint green...",
                "retrieved":  "Type 1, 2, or 3 to select a swatch...",
            }
            placeholder = placeholder_map.get(cur, "Type your message...")

            user_input = st.text_input(
                "Your message",
                placeholder=placeholder,
                label_visibility="collapsed",
                key=f"text_input_{len(st.session_state['history'])}",
            )
            if st.button("Send", key="send_btn") and user_input.strip():
                _send_message(user_input.strip())
                st.rerun()

            if cur in ("greeting", "collecting") and len(st.session_state["history"]) <= 1:
                st.markdown(
                    '<div style="margin-top:0.6rem;"></div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="section-label">{_t("Try saying...", "यह कहकर देखें...")}</div>',
                    unsafe_allow_html=True,
                )
                examples = _t(
                    [
                        "Light saree for summer wedding, Rs.1500",
                        "Shaadi ke liye flowy cotton, around Rs.2000",
                        "Something royal for reception, deep red silk, Rs.8000",
                        "Breathable office saree, Rs.700, navy blue",
                    ],
                    [
                        "गर्मियों की शादी के लिए हल्की साड़ी, Rs.1500",
                        "शादी के लिए फ्लोई कॉटन, लगभग Rs.2000",
                        "रिसेप्शन के लिए रॉयल साड़ी, गहरा लाल सिल्क, Rs.8000",
                        "ऑफिस के लिए सांस लेने वाली साड़ी, Rs.700",
                    ],
                )
                cols = st.columns(2)
                for i, ex in enumerate(examples):
                    with cols[i % 2]:
                        if st.button(ex, key=f"ex_{i}"):
                            _send_message(ex)
                            st.rerun()


# ---------------------------------------------------------------------------
# WEAVER PAGE
# ---------------------------------------------------------------------------
def _weaver_page() -> None:
    _init_weaver_state()

    weavers = _load_weaver_profiles()

    st.markdown(
        '<div class="section-label">Weaver Dashboard</div>',
        unsafe_allow_html=True,
    )

    with st.expander("How to use this app (Weaver)"):
        st.markdown("""
**Step 1 — Select your weaver profile.**
Use the dropdown to log in as yourself. Your cluster, speciality,
rating, and completed orders appear alongside.

**Step 2 — Review pending orders.**
New orders broadcast by the Pakshi agent appear under Pending.
Each card shows the fabric, weave style, colour, occasion,
buyer description, price, and delivery deadline.

**Step 3 — Accept or decline.**
Click Accept to take the order — production begins.
Click Decline if you cannot fulfil it; the agent finds another weaver.

**Step 4 — Upload a progress photo.**
Once weaving starts, upload a mid-production photo.
It is shared with the buyer for preview and builds trust before delivery.

**Step 5 — Simulate a new broadcast.**
Click Simulate New Order Broadcast to see how incoming orders
arrive in real time during the demo.
        """)

    if not weavers:
        st.warning(
            "No weaver profiles found. "
            "Make sure weaver_profiles.json is in the same folder as app.py."
        )
        return

    col_sel, col_stat = st.columns([2, 3])
    with col_sel:
        weaver_options = [
            f"{w['id']} — {w.get('name','Unknown')} ({w.get('cluster','')})"
            for w in weavers[:10]
        ]
        selected = st.selectbox(
            "Logged in as",
            weaver_options,
            label_visibility="collapsed",
        )
        wid = selected.split(" — ")[0] if selected else ""
        st.session_state["weaver_id"] = wid

    profile = next((w for w in weavers if w.get("id") == wid), {})

    with col_stat:
        if profile:
            specialities = ", ".join(profile.get("fabric_specialty", [])) or "—"
            st.markdown(f"""
            <div style="display:flex;gap:1.5rem;align-items:center;padding:0.5rem 0;flex-wrap:wrap;">
                <div>
                    <div class="swatch-label">Cluster</div>
                    <div class="swatch-value" style="font-size:0.85rem;">
                        {profile.get("cluster", "—")}
                    </div>
                </div>
                <div>
                    <div class="swatch-label">Speciality</div>
                    <div class="swatch-value" style="font-size:0.85rem;">
                        {specialities}
                    </div>
                </div>
                <div>
                    <div class="swatch-label">Rating</div>
                    <div class="swatch-value" style="font-size:0.85rem;">
                        {profile.get("rating", "—")}
                    </div>
                </div>
                <div>
                    <div class="swatch-label">Orders done</div>
                    <div class="swatch-value" style="font-size:0.85rem;">
                        {profile.get("orders_completed", "—")}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="pakshi-divider"></div>', unsafe_allow_html=True)

    orders  = st.session_state["weaver_orders"]
    pending  = [o for o in orders if o.get("status") == "pending"]
    accepted = [o for o in orders if o.get("status") == "accepted"]
    declined = [o for o in orders if o.get("status") == "declined"]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="card" style="text-align:center;">
            <div style="font-size:1.8rem;font-weight:800;color:var(--accent-primary);">
                {len(pending)}
            </div>
            <div class="swatch-label">Pending</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="card" style="text-align:center;">
            <div style="font-size:1.8rem;font-weight:800;color:#22c55e;">
                {len(accepted)}
            </div>
            <div class="swatch-label">Accepted</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        total_value = sum(o.get("price", 0) for o in accepted)
        st.markdown(f"""
        <div class="card" style="text-align:center;">
            <div style="font-size:1.8rem;font-weight:800;color:var(--accent-primary);">
                Rs.{total_value:,}
            </div>
            <div class="swatch-label">Value in hand</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:0.4rem;"></div>', unsafe_allow_html=True)

    if pending:
        st.markdown(
            '<div class="section-label">New Orders — Awaiting Your Response</div>',
            unsafe_allow_html=True,
        )
        for order in pending:
            idx = next(
                (i for i, o in enumerate(orders) if o.get("order_id") == order.get("order_id")),
                None,
            )
            if idx is None:
                continue

            feel_tags = "".join(
                f'<span class="tag">{t.strip()}</span>'
                for t in str(order.get("buyer_feel", "")).split(",")[:4]
                if t.strip()
            )
            st.markdown(f"""
            <div class="order-card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div>
                        <div style="font-weight:700;font-size:0.95rem;color:var(--text-white);">
                            {order.get("weave_style","—")} · {order.get("color","—")}
                        </div>
                        <div style="font-size:0.78rem;color:var(--text-muted);margin-top:2px;">
                            Order #{order.get("order_id","—")} · {order.get("occasion","—")}
                        </div>
                    </div>
                    <div class="swatch-price">Rs.{order.get("price",0):,}</div>
                </div>
                <div style="margin-top:8px;font-size:0.82rem;color:var(--text-primary);">
                    <b>Buyer says:</b> "{order.get("buyer_note","")}"
                </div>
                <div style="margin-top:6px;">{feel_tags}</div>
                <div style="margin-top:8px;font-size:0.78rem;color:var(--text-muted);">
                    Deliver by {order.get("delivery_by","—")}
                </div>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, _ = st.columns([1, 1, 3])
            with c1:
                if st.button(
                    "Accept",
                    key=f"acc_{order['order_id']}",
                    use_container_width=True,
                ):
                    st.session_state["weaver_orders"][idx]["status"] = "accepted"
                    order_summary = (
                        f"New order: {order.get('weave_style','')}, "
                        f"{order.get('color','')}, "
                        f"Rs.{order.get('price',0)}, "
                        f"due {order.get('delivery_by','')}"
                    )
                    audio_bytes = _tts_bytes(order_summary, lang="en")
                    if audio_bytes:
                        _autoplay_audio(audio_bytes)
                        st.caption("Listen to order details above")
                    else:
                        st.info("Audio playback not available. Order accepted.")
                    st.success(
                        f"Order {order.get('order_id','')} accepted! Buyer will be notified."
                    )
                    time.sleep(0.4)
                    st.rerun()

            with c2:
                if st.button(
                    "Decline",
                    key=f"dec_{order['order_id']}",
                    use_container_width=True,
                ):
                    st.session_state["weaver_orders"][idx]["status"] = "declined"
                    st.info("Order declined. Agent will find another weaver.")
                    time.sleep(0.4)
                    st.rerun()

    if accepted:
        st.markdown(
            '<div class="section-label" style="margin-top:1rem;">In Production</div>',
            unsafe_allow_html=True,
        )
        for order in accepted:
            idx = next(
                (i for i, o in enumerate(orders) if o.get("order_id") == order.get("order_id")),
                None,
            )
            st.markdown(f"""
            <div class="order-card accepted">
                <div style="display:flex;justify-content:space-between;">
                    <div>
                        <div style="font-weight:700;font-size:0.9rem;color:var(--text-white);">
                            {order.get("weave_style","—")} · {order.get("color","—")}
                        </div>
                        <div style="font-size:0.75rem;color:var(--text-muted);">
                            #{order.get("order_id","—")} · Due {order.get("delivery_by","—")}
                        </div>
                    </div>
                    <div class="state-badge state-active">In Production</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            uploaded = st.file_uploader(
                f"Upload progress photo for {order.get('order_id','')}",
                type=["jpg", "jpeg", "png"],
                key=f"photo_{order.get('order_id','')}",
                label_visibility="collapsed",
            )
            if uploaded is not None:
                try:
                    st.image(
                        uploaded,
                        caption=f"Progress: {order.get('order_id','')}",
                        width=280,
                    )
                    st.success("Photo sent to buyer for preview!")
                    if idx is not None:
                        st.session_state["weaver_orders"][idx]["photo"] = uploaded.name
                    for bo in st.session_state.get("buyer_orders", []):
                        if bo.get("order_id") == order.get("order_id"):
                            bo["photo_path"] = uploaded.name
                            bo["status"]     = "Photo Available"
                            break
                except Exception as exc:
                    st.error(f"Could not display photo: {exc}")

            st.markdown('<div style="height:0.4rem;"></div>', unsafe_allow_html=True)

    if declined:
        st.markdown(
            '<div class="section-label" style="margin-top:1rem;color:var(--text-muted);">Declined</div>',
            unsafe_allow_html=True,
        )
        for order in declined:
            st.markdown(f"""
            <div class="order-card declined">
                <span style="font-size:0.85rem;color:var(--text-primary);">
                    {order.get("weave_style","—")} · #{order.get("order_id","—")}
                </span>
                <span style="float:right;font-size:0.75rem;color:var(--text-muted);">
                    Declined
                </span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)
    if st.button("Simulate New Order Broadcast"):
        weave_style = profile.get("weave_style", "Handloom") if profile else "Handloom"
        new_order = {
            "order_id":   f"PKS-{random.randint(2900, 2999)}",
            "fabric":     random.choice(["Cotton-Silk", "Cotton", "Silk"]),
            "weave_style": weave_style,
            "color":      random.choice(["Sage green", "Mustard yellow", "Ivory with zari", "Teal"]),
            "occasion":   random.choice(["Wedding", "Festival", "Casual"]),
            "buyer_feel": random.choice(["light, flowy, elegant", "royal, heavy, grand", "breathable, cool"]),
            "price":      random.choice([900, 1200, 1500, 2000, 2500]),
            "delivery_by":"July 25, 2026",
            "status":     "pending",
            "photo":      None,
            "buyer_note": "New broadcast from Pakshi agent",
        }
        st.session_state["weaver_orders"].insert(0, new_order)
        st.success("New order broadcast received!")
        st.rerun()


# ---------------------------------------------------------------------------
# ONE OF A KIND PAGE
# ---------------------------------------------------------------------------
def _one_of_a_kind_page() -> None:
    st.markdown(
        '<div class="section-label">One of a Kind — Rejected Custom Pieces</div>',
        unsafe_allow_html=True,
    )

    items: list[dict] = st.session_state.get("one_of_a_kind", [])

    if not items:
        st.markdown("""
        <div class="card" style="text-align:center;padding:2.5rem;">
            <div style="font-weight:700;font-size:1rem;margin-bottom:0.4rem;
                        color:var(--text-white);">
                No rejected pieces yet — that is a good sign
            </div>
            <div style="font-size:0.82rem;color:var(--text-muted);line-height:1.6;">
                When a custom order does not meet a buyer's expectation,<br>
                it lands here at wholesale price.<br>
                <span style="color:var(--accent-primary);font-weight:600;">
                    No waste. No loss. Every piece finds a buyer.
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    count = len(items)
    st.caption(
        f"{count} unique handwoven piece{'s' if count > 1 else ''} available "
        "at wholesale prices — ready to ship, each one of a kind."
    )
    st.markdown('<div class="pakshi-divider"></div>', unsafe_allow_html=True)

    for idx, item in enumerate(items):
        original = item.get("original_price", 0)
        resale   = item.get("resale_price",   0)
        discount = int((1 - resale / original) * 100) if original > 0 else 0
        tags_html = "".join(
            f'<span class="tag">{t}</span>'
            for t in item.get("sensory_tags", [])[:3]
        )

        col1, col2 = st.columns([4, 1], gap="small")
        with col1:
            st.markdown(f"""
            <div class="card">
                <div style="display:flex;justify-content:space-between;
                    align-items:flex-start;flex-wrap:wrap;gap:0.5rem;">
                    <div>
                        <div style="font-weight:700;font-size:1rem;color:var(--text-white);">
                            {item.get("weave_style","—")} &nbsp;·&nbsp; {item.get("color","—")}
                        </div>
                        <div style="font-size:0.78rem;color:var(--text-muted);margin-top:3px;">
                            Order #{item.get("order_id","—")} · {item.get("reason","—")}
                        </div>
                        <div style="margin:8px 0;">
                            {tags_html}
                            <span class="tag" style="background:rgba(34,197,94,0.15);
                                color:#22c55e;">wholesale</span>
                            <span class="tag" style="background:rgba(34,197,94,0.15);
                                color:#22c55e;">ready to ship</span>
                            <span class="tag" style="background:rgba(239,68,68,0.15);
                                color:#ef4444;">rejected custom</span>
                        </div>
                        <div style="font-size:0.82rem;color:var(--text-primary);">
                            Woven by <b>{item.get("weaver_name","—")}</b> ·
                            {item.get("weaver_cluster","—")}, {item.get("weaver_state","—")}
                        </div>
                    </div>
                    <div style="text-align:right;flex-shrink:0;">
                        <div style="font-size:0.78rem;color:var(--text-muted);
                            text-decoration:line-through;">
                            Rs.{original:,}
                        </div>
                        <div class="swatch-price">Rs.{resale:,}</div>
                        <div style="background:rgba(34,197,94,0.2);color:#22c55e;
                            padding:2px 8px;border-radius:999px;font-size:0.72rem;
                            font-weight:700;display:inline-block;margin-top:2px;">
                            {discount}% off
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown('<div style="height:0.6rem;"></div>', unsafe_allow_html=True)
            if st.button(
                "Buy Now",
                key=f"buy_{item.get('order_id', '')}_{idx}",
                use_container_width=True,
            ):
                st.success(
                    f"{item.get('order_id','')} added to cart! "
                    "Estimated delivery: 3-5 days."
                )

        st.markdown('<div style="height:0.2rem;"></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main() -> None:
    _render_header()

    if "app_loaded" not in st.session_state:
        st.markdown(
            '<div style="background:rgba(218,65,103,0.1);'
            'border:1px solid rgba(218,65,103,0.3);'
            'border-radius:8px;padding:0.5rem 1rem;font-size:0.82rem;'
            'color:var(--accent-primary);margin-bottom:0.8rem;">'
            'First load — agent is warming up. '
            'This takes about 15 seconds. Subsequent responses will be faster.</div>',
            unsafe_allow_html=True,
        )
        st.session_state["app_loaded"] = True

    tab = st.radio(
        "View",
        ["Buyer — Describe Your Saree", "Weaver — Manage Orders", "One of a Kind — Resale"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown('<div class="pakshi-divider"></div>', unsafe_allow_html=True)

    if "Buyer" in tab:
        _buyer_page()
    elif "Weaver" in tab:
        _weaver_page()
    else:
        _one_of_a_kind_page()


if __name__ == "__main__":
    main()
