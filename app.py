"""
Pakshi - Full Streamlit App (Tier-2/3 Buyer & Artisan Optimized)
================================================================
Buyer  : Bilingual voice/text input -> agent matches swatches -> trust-first confirmation
Weaver : Hands-free bidirectional audio commands (Accept/Reject/Show Buyer) + Min Base Filter
OOAK   : Zero-waste wholesale listing for rejected custom pieces
Onboard: Persists new weavers into the live dashboard.

Run:
    pip install streamlit chromadb scikit-learn edge-tts SpeechRecognition
    streamlit run app.py
"""

import base64
import json
import os
import random
import re
import tempfile
import time
import asyncio
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Pakshi — Handloom Direct",
    page_icon="🪶",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Brand & Tier-2/3 Touch-Friendly CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg-deep:        #19031c;
    --bg-surface:     #2d0d2a;
    --bg-card:        #52104c;
    --bg-card-2:      #8a1c7c;
    --accent:         #da4167;
    --accent-glow:    rgba(218,65,103,0.35);
    --text-primary:   #f0bcd4;
    --text-muted:     #9c8a95;
    --text-white:     #ffffff;
    --success:        #22c55e;
    --warning:        #f59e0b;
    --danger:         #ef4444;
    --border:         rgba(240,188,212,0.15);
    --border-strong:  rgba(240,188,212,0.25);
}

html, body { background-color: var(--bg-deep) !important; }
.stApp { background-color: var(--bg-deep) !important; font-family: 'Inter', sans-serif !important; }
.main .block-container {
    padding: 1.5rem 2rem 4rem !important;
    max-width: 1140px !important;
    background-color: var(--bg-deep) !important;
}
section[data-testid="stSidebar"] { background-color: var(--bg-surface) !important; }
#MainMenu, footer, header { visibility: hidden !important; }

p, li, span, label { color: var(--text-primary); font-family: 'Inter', sans-serif !important; }
h1, h2, h3 { color: var(--text-white) !important; font-family: 'Inter', sans-serif !important; }

.wordmark {
    font-size: 2.2rem; font-weight: 800;
    color: var(--text-white); letter-spacing: -0.8px; line-height: 1.1;
}
.wordmark span { color: var(--accent); }
.tagline {
    font-size: 0.85rem; color: var(--text-muted);
    margin-top: 2px; margin-bottom: 0; letter-spacing: 0.02em;
}

.meesho-badge {
    font-size: 0.70rem; color: #fff;
    background: linear-gradient(90deg, rgba(218,65,103,0.25), rgba(138,28,124,0.35));
    border: 1px solid rgba(218,65,103,0.4);
    padding: 3px 12px; border-radius: 999px;
    display: inline-block; margin-top: 6px;
    letter-spacing: 0.05em; font-weight: 600;
}

.trust-banner {
    display: flex; gap: 1rem; align-items: center; justify-content: space-around;
    background: rgba(34,197,94,0.08); border: 1px solid rgba(34,197,94,0.25);
    border-radius: 10px; padding: 0.6rem 1rem; margin-bottom: 1.2rem;
    font-size: 0.80rem; color: #86efac; font-weight: 600; text-align: center;
}

.card {
    background: rgba(45,13,42,0.75);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border-strong);
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.9rem;
    color: var(--text-primary);
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.card:hover { transform: translateY(-2px); box-shadow: 0 8px 28px rgba(0,0,0,0.45); }

.swatch-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-strong);
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.6rem;
}
.swatch-price { font-size: 1.5rem; font-weight: 800; color: var(--accent); line-height: 1.1; }
.swatch-label {
    font-size: 0.68rem; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.1em;
    margin-top: 0.7rem; margin-bottom: 0.1rem;
}
.swatch-value { font-size: 0.9rem; font-weight: 600; color: var(--text-white); }

.tag {
    display: inline-block; padding: 2px 9px; border-radius: 999px;
    background: rgba(218,65,103,0.15); color: var(--accent);
    font-size: 0.7rem; font-weight: 600; margin: 2px 2px 0 0;
    border: 1px solid rgba(218,65,103,0.25);
}

.tag-warning {
    display: inline-block; padding: 3px 10px; border-radius: 999px;
    background: rgba(245,158,11,0.15); color: var(--warning);
    font-size: 0.72rem; font-weight: 700; margin: 2px 2px 0 0;
    border: 1px solid rgba(245,158,11,0.35);
}

.chat-wrap { display: flex; flex-direction: column; gap: 0.3rem; padding-bottom: 0.5rem; }
.bubble-agent {
    background: var(--bg-surface);
    border: 1px solid var(--border-strong);
    border-radius: 14px 14px 14px 3px;
    padding: 0.8rem 1rem;
    max-width: 86%;
    font-size: 0.90rem; line-height: 1.6;
    white-space: pre-wrap; color: var(--text-primary);
    align-self: flex-start;
}
.bubble-user {
    background: var(--bg-card-2);
    border: 1px solid rgba(218,65,103,0.2);
    border-radius: 14px 14px 3px 14px;
    padding: 0.8rem 1rem;
    max-width: 74%;
    font-size: 0.90rem; line-height: 1.6;
    color: var(--text-white);
    align-self: flex-end; text-align: right;
}

.section-label {
    font-size: 0.72rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.14em;
    color: var(--accent); margin-bottom: 0.45rem;
}
.divider { height: 1px; background: var(--border); margin: 1.1rem 0; }

.confirmed-banner {
    background: linear-gradient(135deg,rgba(34,197,94,0.15),rgba(34,197,94,0.03));
    border: 1.5px solid rgba(34,197,94,0.5);
    border-radius: 14px; padding: 1.4rem; text-align: center; margin-top: 1rem;
}
.confirmed-banner h2 { color: #22c55e !important; margin: 0; font-size: 1.5rem; }

.order-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-strong);
    border-radius: 12px;
    padding: 1rem 1.2rem; margin-bottom: 0.75rem;
}
.order-card.accepted { border-color: rgba(34,197,94,0.35); background: rgba(34,197,94,0.04); }
.order-card.declined { border-color: rgba(239,68,68,0.25); opacity: 0.55; }
.order-card.below-base { border-color: rgba(245,158,11,0.45); background: rgba(245,158,11,0.04); }

.state-badge {
    display: inline-block; padding: 3px 10px; border-radius: 999px;
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase;
}
.state-active  { background: rgba(34,197,94,0.18);  color: #22c55e; border: 1px solid rgba(34,197,94,0.3); }
.state-pending { background: rgba(218,65,103,0.15); color: var(--accent); border: 1px solid rgba(218,65,103,0.3); }

.step-row { display: flex; align-items: center; gap: 0.55rem; font-size: 0.82rem; }
.step-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.step-dot.done    { background: #22c55e; box-shadow: 0 0 5px rgba(34,197,94,0.5); }
.step-dot.active  { background: var(--accent); box-shadow: 0 0 6px var(--accent-glow); }
.step-dot.pending { background: var(--bg-card); opacity: 0.35; }

.stTextInput input,
.stTextArea textarea {
    background-color: var(--bg-surface) !important;
    color: var(--text-white) !important;
    border: 1.5px solid var(--bg-card) !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    caret-color: var(--accent) !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(218,65,103,0.22) !important;
    outline: none !important;
}

.stButton > button {
    background: var(--accent) !important;
    color: var(--text-white) !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 9px !important;
    padding: 0.6rem 1.4rem !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.90rem !important;
    transition: opacity 0.15s, box-shadow 0.15s !important;
    letter-spacing: 0.01em !important;
}
.stButton > button:hover {
    opacity: 0.88 !important;
    box-shadow: 0 0 18px var(--accent-glow) !important;
}
.stButton > button:active { opacity: 0.75 !important; }

div[role="radiogroup"] {
    display: flex !important;
    gap: 0.3rem !important;
    background: var(--bg-surface) !important;
    padding: 4px !important;
    border-radius: 10px !important;
    border: 1px solid var(--border-strong) !important;
    width: fit-content !important;
}
div[role="radiogroup"] label {
    padding: 0.4rem 1rem !important;
    border-radius: 7px !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    color: var(--text-muted) !important;
    transition: background 0.15s, color 0.15s !important;
}
div[role="radiogroup"] label:has(input:checked) {
    background: var(--accent) !important;
    color: var(--text-white) !important;
}
div[role="radiogroup"] input[type="radio"] { display: none !important; }

.stSelectbox > div > div {
    background-color: var(--bg-surface) !important;
    color: var(--text-white) !important;
    border: 1.5px solid var(--bg-card) !important;
    border-radius: 9px !important;
}

details summary { color: var(--accent) !important; font-weight: 600 !important; font-size: 0.88rem !important; }
.stCaption { color: var(--text-muted) !important; font-size: 0.78rem !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Cached backend loaders
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
# Edge TTS & STT (Text-to-Speech & Speech-to-Text)
# ---------------------------------------------------------------------------
_EDGE_TTS_VOICES = {
    "hi": "hi-IN-MadhurNeural",
    "en": "en-IN-PrabhatNeural",
}

def _tts_edge(text: str, lang: str = "hi") -> bytes | None:
    if not text:
        return None
    voice = _EDGE_TTS_VOICES.get(lang, "hi-IN-MadhurNeural")
    spoken = ". ".join(text.split(". ")[:3]).strip()
    if not spoken:
        return None
    try:
        import edge_tts
        async def generate():
            communicate = edge_tts.Communicate(spoken, voice)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                tmp_path = tmp.name
            await communicate.save(tmp_path)
            return tmp_path

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        tmp_path = loop.run_until_complete(generate())
        with open(tmp_path, "rb") as f:
            data = f.read()
        try: os.unlink(tmp_path)
        except OSError: pass
        return data
    except Exception as e:
        print(f"Edge TTS error: {e}")
        return None

def _tts_bytes(text: str, lang: str = "hi") -> bytes | None:
    return _tts_edge(text, lang)

def _autoplay_audio(audio_bytes: bytes, fmt: str = "mp3", label: str = "") -> None:
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(
        f'<audio controls autoplay style="width:100%;margin:4px 0;border-radius:6px;">'
        f'<source src="data:audio/{fmt};base64,{b64}" type="audio/{fmt}">'
        f'</audio>',
        unsafe_allow_html=True,
    )
    if label:
        st.caption(f"{label} — press play if audio did not start.")

def _stt_google(audio_bytes: bytes) -> tuple[str | None, str | None]:
    if len(audio_bytes) < 8_000:
        return None, "Recording too short — please speak clearly for at least 2 seconds."
    try:
        import speech_recognition as sr
    except ImportError:
        return None, "SpeechRecognition library not installed. Please type your request."

    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 0.8
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with sr.AudioFile(tmp_path) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio, language="hi-IN")
            if text and len(text.strip()) > 1: return text.strip(), None
        except sr.UnknownValueError: pass
        except sr.RequestError as e: return None, f"Speech recognition service unavailable: {e}"

        try:
            text = recognizer.recognize_google(audio, language="en-IN")
            if text and len(text.strip()) > 1: return text.strip(), None
        except sr.UnknownValueError: pass
        except sr.RequestError as e: return None, f"Speech recognition service unavailable: {e}"

        return None, "Could not understand. Please speak clearly in Hindi or English."
    except Exception as e:
        return None, f"Speech recognition error: {e}"
    finally:
        try: os.unlink(tmp_path)
        except OSError: pass

def _transcribe_audio(audio_file) -> tuple[str | None, str | None]:
    buf = audio_file.getbuffer()
    return _stt_google(bytes(buf))

# ---------------------------------------------------------------------------
# Natural Language Voice Command Parsers
# ---------------------------------------------------------------------------
_CORRECTION_PHRASES = {
    "not what i want", "that's not", "thats not", "wrong", "not this",
    "different", "no not", "not these", "show me something else",
    "change", "none of these", "not right", "not matching",
    "not kanchipuram", "not silk", "not cotton", "not banarasi",
    "not pochampally", "search again", "try again", "redo",
    "not for me", "nahi chahiye", "aur dikhao", "kuch aur", "doosra dikhao"
}

def _is_correction(text: str) -> bool:
    t = text.lower().strip()
    return any(phrase in t for phrase in _CORRECTION_PHRASES)

def _is_number_selection(text: str) -> bool:
    t = text.lower().strip()
    return t in {"1", "2", "3", "one", "two", "three", "first", "second", "third", "ek", "do", "teen", "pehla", "doosra", "teesra"}

def _parse_weaver_voice_command(text: str, pending: list, accepted: list) -> dict | None:
    """
    Parses natural Hindi/English voice commands from the weaver to accept, reject,
    or show the fabric to the buyer hands-free.
    Now handles missing order numbers, more keywords, and fallback defaults.
    """
    t = text.lower()
    action = None

    # 1. Determine Intent – expanded with more Hindi variations
    accept_words = {"swikaar", "accept", "le lo", "manzoor", "pakka", "done", "han", "haan", "ok", "theek", "yes", "y", "sahi"}
    reject_words = {"mana", "reject", "decline", "cancel", "nahi", "chhod", "no", "n", "galat", "wrong", "cancel"}
    show_words = {"dikhao", "show", "bhejo", "send", "photo", "tasveer", "approve", "buyer", "dekhao"}

    if any(w in t for w in accept_words):
        action = "accept"
    elif any(w in t for w in reject_words):
        action = "decline"
    elif any(w in t for w in show_words):
        action = "show_buyer"

    if not action:
        return {"action": "error", "message": "Could not understand command. Try 'Accept first order', 'Reject order 2847', or 'Show buyer'."}

    # 2. Determine which list to target (pending for accept/decline, accepted for show)
    target_list = accepted if action == "show_buyer" else pending
    if not target_list:
        return {"action": "error", "message": f"No {'in-production' if action == 'show_buyer' else 'pending'} orders available."}

    target_idx = None

    # 3. Try to extract a 4-digit order ID (e.g., 2847)
    m = re.search(r'\b(\d{4})\b', t)
    if m:
        oid = m.group(1)
        for i, o in enumerate(target_list):
            if oid in o.get("order_id", ""):
                target_idx = i
                break

    # 4. If no ID, try ordinal words (first, second, third)
    if target_idx is None:
        ordinals = {
            "first": 0, "pehla": 0, "1": 0, "one": 0, "ek": 0,
            "second": 1, "doosra": 1, "2": 1, "two": 1, "do": 1,
            "third": 2, "teesra": 2, "3": 2, "three": 2, "teen": 2
        }
        for word, idx in ordinals.items():
            if word in t:
                if idx < len(target_list):
                    target_idx = idx
                break

    # 5. If still no match and there's only one order, default to it
    if target_idx is None and len(target_list) == 1:
        target_idx = 0

    if target_idx is not None and target_idx < len(target_list):
        return {
            "action": action,
            "order_id": target_list[target_idx]["order_id"],
            "weave_style": target_list[target_idx].get("weave_style", "")
        }

    return {"action": "error", "message": "Could not identify which order. Please say the 4‑digit order ID (e.g., 2847) or 'first order'."}

# ---------------------------------------------------------------------------
# Session state initializers
# ---------------------------------------------------------------------------
def _init_buyer_state() -> None:
    defaults = {
        "agent": None, "history": [], "current_state": "greeting", "swatches": [],
        "selected_swatch": None, "order": None, "agent_data": {}, "awaiting": None,
        "reasoning_log": [], "one_of_a_kind": [], "buyer_orders": [], "agent_thinking": False,
        "prefill_text": "", "greeted": False, "audio_counter": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def _init_weaver_state() -> None:
    if "weaver_orders" not in st.session_state: st.session_state["weaver_orders"] = _make_demo_orders()
    if "weaver_id" not in st.session_state: st.session_state["weaver_id"] = "W001"
    if "min_base_price" not in st.session_state: st.session_state["min_base_price"] = 1000
    if "audio_work_mode" not in st.session_state: st.session_state["audio_work_mode"] = False
    if "weaver_audio_counter" not in st.session_state: st.session_state["weaver_audio_counter"] = 0
    if "custom_weavers" not in st.session_state: st.session_state["custom_weavers"] = []

def _make_demo_orders() -> list:
    return [
        {
            "order_id": "PKS-2847", "fabric": "Cotton-Silk", "weave_style": "Pochampally Ikat",
            "color": "Teal with gold border", "occasion": "Summer Wedding", "buyer_feel": "flowy, breathable yet elegant",
            "price": 1800, "delivery_by": "July 26, 2026", "status": "pending", "photo": None,
            "buyer_note": "Light saree, summer wedding, Rs.1500 - agent proposed Cotton-Silk",
            "weaver_location": "Pochampally",
        },
        {
            "order_id": "PKS-2831", "fabric": "Cotton", "weave_style": "Pochampally Ikat",
            "color": "Navy blue", "occasion": "Office / Daily Wear", "buyer_feel": "breathable, cool",
            "price": 750, "delivery_by": "July 20, 2026", "status": "accepted", "photo": None,
            "buyer_note": "Office wear, breathable cotton under Rs.800", "weaver_location": "Pochampally",
        }
    ]

# ---------------------------------------------------------------------------
# Get all weavers (built-in + custom)
# ---------------------------------------------------------------------------
def _get_all_weavers() -> list:
    builtin = _load_weaver_profiles()
    custom = st.session_state.get("custom_weavers", [])
    return builtin + custom

# ---------------------------------------------------------------------------
# Header & UI Elements
# ---------------------------------------------------------------------------
def _render_header() -> None:
    st.markdown(
        '<div style="display:flex;align-items:center;justify-content:space-between;'
        'padding:0.5rem 0 0.8rem;border-bottom:1px solid rgba(240,188,212,0.10);margin-bottom:1rem;">'
        '<div>'
        '<div class="wordmark">Pak<span>shi</span> 🪶</div>'
        '<div class="tagline">Direct from India\'s Master Weavers · Zero Middlemen Markup</div>'
        '<div class="meesho-badge">🪢 Meesho Verified Made-to-Order Handloom Vertical</div>'
        '</div>'
        '<div style="font-size:0.75rem;color:rgba(240,188,212,0.4);font-weight:600;text-align:right;">'
        '100% ARTISAN DIRECT<br><span style="color:#22c55e;">CASH ON DELIVERY AVAILABLE</span>'
        '</div></div>', unsafe_allow_html=True,
    )

_STATE_STEPS = [
    ("greeting", "Start"), ("collecting", "Describe Intent"), ("retrieved", "Select Swatch"),
    ("fallback_pending", "Fallback"), ("swatch_selected", "Lock Fabric"),
    ("broadcasting", "Broadcast"), ("weaver_selected", "Matched"), ("confirmed", "Order Placed"),
]
_HIDDEN_STATES = {"fallback_pending", "broadcasting", "weaver_selected"}

def _step_indicator(current: str) -> None:
    active = next((i for i, (k, _) in enumerate(_STATE_STEPS) if k == current), 0)
    parts = ['<div style="display:flex;gap:1.2rem;align-items:center;margin-bottom:1rem;flex-wrap:wrap;">']
    for i, (key, label) in enumerate(_STATE_STEPS):
        if key in _HIDDEN_STATES: continue
        cls = "done" if i < active else ("active" if i == active else "pending")
        color = "#22c55e" if cls == "done" else ("var(--accent)" if cls == "active" else "var(--text-muted)")
        parts.append(
            f'<div class="step-row"><div class="step-dot {cls}"></div>'
            f'<span style="font-size:0.80rem;color:{color};font-weight:600;">{label}</span></div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)

def _swatch_card(swatch: dict, index: int) -> None:
    tags = "".join(f'<span class="tag">{t}</span>' for t in swatch.get("sensory_tags", [])[:3])
    location = swatch.get("weaver_state", "")
    if swatch.get("weaver_cluster"): location = f"{swatch.get('weaver_cluster')}, {location}"

    reviews_html = "".join(
        f'<div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px;">{"⭐"*int(r.get("rating",5))} '
        f'<span style="color:var(--text-primary);">{r.get("user","")}</span>: "{r.get("comment","")}"</div>'
        for r in (swatch.get("reviews", []) or [])[:2]
    )

    st.markdown(f"""
    <div class="swatch-card" style="border: 1.5px solid {'var(--accent)' if index == 0 else 'var(--border-strong)'};">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span style="background:var(--bg-card);color:var(--text-primary);padding:2px 8px;border-radius:6px;font-size:0.75rem;font-weight:700;">Option {index + 1}</span>
            <span style="color:#22c55e;font-size:0.75rem;font-weight:600;">✓ Authentic Handloom</span>
        </div>
        <img src="https://picsum.photos/seed/{swatch.get("swatch_id", "S001")}/300/180"
             style="width:100%;height:160px;object-fit:cover;border-radius:10px;margin-bottom:8px;background:var(--bg-card);"/>
        <div style="font-weight:800;font-size:1.05rem;color:var(--text-white);margin-bottom:2px;">
            {swatch.get("weave_style","—")}
        </div>
        <div style="font-size:0.85rem;color:var(--text-muted);margin-bottom:6px;">
            {swatch.get("color","—")} · <span style="color:var(--accent);font-weight:600;">{location}</span>
        </div>
        <div class="swatch-price">₹{swatch.get("price_inr","?")}</div>
        <div style="font-size:0.72rem;color:#86efac;margin-bottom:6px;">Includes weaver labor & direct home delivery</div>
        <div style="font-size:0.80rem;color:var(--text-primary);line-height:1.55;margin-bottom:6px;opacity:0.9;">
            {swatch.get('description', '')}
        </div>
        <div style="margin:6px 0;">{tags}</div>
        <div class="divider"></div>
        <div class="swatch-label">Master Artisan</div>
        <div class="swatch-value">{swatch.get("weaver_name","—")}</div>
        <div style="font-size:0.80rem;color:var(--text-muted);">{location}</div>
        <div style="margin-top:4px;font-size:0.82rem;color:var(--text-primary);font-weight:600;">
            ⭐ Rating: {swatch.get("weaver_rating","?")} &nbsp;·&nbsp; 🚚 Delivery: {swatch.get("delivery_days","?")} days
        </div>
        {reviews_html}
    </div>
    """, unsafe_allow_html=True)

def _send(user_text: str, *, force_new_search: bool = False) -> None:
    user_text = (user_text or "").strip()
    if not user_text: return
    PakshiAgent, err = _load_agent_class()
    if err or PakshiAgent is None: return st.error(f"Backend not loaded: {err}")

    if force_new_search:
        st.session_state["swatches"] = []
        st.session_state["agent_data"] = {}
        st.session_state["current_state"] = "collecting"
        st.session_state["agent"] = None

    if st.session_state.get("agent") is None:
        try: st.session_state["agent"] = PakshiAgent()
        except Exception as exc: return st.error(f"Agent init failed: {exc}")

    st.session_state["history"].append(("user", user_text))
    st.session_state["agent_thinking"] = True
    try: response = st.session_state["agent"].chat(user_text)
    except Exception as exc:
        st.session_state["agent_thinking"] = False
        return st.session_state["history"].append(("agent", f"Error: {exc}. Please try again."))
    st.session_state["agent_thinking"] = False

    msg = response.get("message", "") if isinstance(response, dict) else str(response)
    state = response.get("state", "greeting") if isinstance(response, dict) else "greeting"
    data = response.get("data", {}) if isinstance(response, dict) else {}

    st.session_state["current_state"] = state
    st.session_state["history"].append(("agent", msg))
    st.session_state["agent_data"] = data
    if data.get("swatches"): st.session_state["swatches"] = data["swatches"]
    if data.get("order"): st.session_state["order"] = data["order"]

    if state == "confirmed" and data.get("order"):
        raw = data["order"]
        sw, wv = raw.get("selected_swatch") or {}, raw.get("selected_weaver") or {}
        entry = {
            "order_id": raw.get("order_id", "PKS-???"),
            "weave_style": sw.get("weave_style", "—"), "color": sw.get("color", "—"),
            "price": sw.get("price_inr", 0), "weaver_name": wv.get("weaver_name", "—"),
            "status": "In Production", "photo_path": None,
        }
        if entry["order_id"] not in {o["order_id"] for o in st.session_state.get("buyer_orders", [])}:
            st.session_state["buyer_orders"].append(entry)

    if state in ("fallback_pending", "broadcasting", "weaver_selected", "confirmed"):
        snippet = msg[:120] + ("..." if len(msg) > 120 else "")
        st.session_state["reasoning_log"].append(f"[{state.upper()}] {snippet}")

# ---------------------------------------------------------------------------
# BUYER PAGE
# ---------------------------------------------------------------------------
def _buyer_page() -> None:
    _init_buyer_state()
    st.markdown("""<div class="trust-banner"><span>✅ 100% Handloom Verified</span><span>💵 Pay on Delivery Available</span><span>🚚 Direct Factory Shipping</span></div>""", unsafe_allow_html=True)

    if st.session_state.get("agent_thinking"):
        st.markdown('<div style="background:rgba(218,65,103,0.15);border-left:4px solid var(--accent);padding:0.8rem 1rem;border-radius:0 8px 8px 0;font-size:0.90rem;font-weight:600;color:var(--text-white);margin-bottom:0.8rem;">⏳ Agent is finding matching artisans for you...</div>', unsafe_allow_html=True)

    buyer_orders = st.session_state.get("buyer_orders", [])
    if buyer_orders:
        with st.expander(f"📦 Your Active Orders ({len(buyer_orders)})", expanded=True):
            for bo in buyer_orders:
                status = bo.get("status", "In Production")
                color = {"In Production": "var(--warning)", "Awaiting Approval": "var(--accent)", "Completed": "#22c55e"}.get(status, "var(--text-muted)")

                needs_approval = status == "Awaiting Approval"
                photo_html = f'<div style="margin-top:10px;"><img src="https://picsum.photos/seed/{bo["order_id"]}/400/200" style="width:100%;max-width:300px;border-radius:8px;border:2px solid var(--accent);"></div>' if bo.get("photo_path") else ""

                st.markdown(f"""
                <div style="background:rgba(58,24,112,0.6);border:1px solid var(--border);border-radius:10px;padding:1rem;margin-bottom:0.5rem;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;">
                        <div>
                            <div style="font-weight:800;font-size:1rem;color:var(--text-white);">{bo["weave_style"]} · {bo["color"]}</div>
                            <div style="font-size:0.80rem;color:var(--text-muted);">#{bo["order_id"]} · Artisan: {bo["weaver_name"]} · ₹{bo["price"]:,}</div>
                            {photo_html}
                        </div>
                        <div style="background:rgba(0,0,0,0.4);padding:4px 12px;border-radius:999px;font-size:0.75rem;font-weight:700;color:{color};">{status}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if needs_approval:
                    st.markdown('<div style="font-size:0.85rem;color:var(--text-white);margin-bottom:8px;">The artisan has finished weaving! Review the final fabric above.</div>', unsafe_allow_html=True)
                    a1, a2, _ = st.columns([1, 1, 2])
                    with a1:
                        if st.button("✅ Approve & Ship", key=f"app_{bo['order_id']}", use_container_width=True):
                            bo["status"] = "Completed"
                            for wo in st.session_state.get("weaver_orders", []):
                                if wo["order_id"] == bo["order_id"]: wo["status"] = "completed"
                            st.success(f"Fabric Approved! {bo['weaver_name']} is shipping your order.")
                            st.rerun()
                    with a2:
                        if st.button("❌ Reject Piece", key=f"rej_{bo['order_id']}", use_container_width=True):
                            st.session_state.setdefault("one_of_a_kind", []).append({
                                "order_id": bo["order_id"], "weave_style": bo["weave_style"], "color": bo["color"],
                                "original_price": bo["price"], "resale_price": int(bo["price"] * 0.65),
                                "weaver_name": bo["weaver_name"], "reason": "Buyer rejected final fabric",
                            })
                            st.session_state["buyer_orders"].remove(bo)
                            for wo in st.session_state.get("weaver_orders", []):
                                if wo["order_id"] == bo["order_id"]: wo["status"] = "declined"
                            st.warning("Order Cancelled. Piece moved to Wholesale Outlet.")
                            st.rerun()

    _step_indicator(st.session_state["current_state"])
    col_chat, col_panel = st.columns([3, 2], gap="large")

    with col_panel:
        swatches = st.session_state["swatches"]
        if swatches:
            st.markdown('<div class="section-label">🎨 Recommended Artisanal Swatches</div>', unsafe_allow_html=True)
            for i, sw in enumerate(swatches[:3]):
                _swatch_card(sw, i)
                if st.session_state["current_state"] == "retrieved":
                    if st.button(f"👉 Select Option {i + 1}", key=f"sel_{i}", use_container_width=True):
                        _send(str(i + 1)); st.rerun()
            if st.session_state["current_state"] == "retrieved":
                st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
                if st.button("🔄 None of these — Show Different Options", use_container_width=True, key="none_of_these"):
                    _send("search again", force_new_search=True); st.rerun()

    with col_chat:
        if st.session_state["history"]:
            st.markdown(f'<div class="chat-wrap">{"".join(f"<div class={chr(34)}{'bubble-agent' if r=='agent' else 'bubble-user'}{chr(34)}>{t}</div>" for r, t in st.session_state["history"])}</div>', unsafe_allow_html=True)

        cur = st.session_state["current_state"]
        if cur == "fallback_pending":
            c1, c2 = st.columns(2)
            if c1.button("✅ Yes, Show Alternatives", use_container_width=True): _send("yes"); st.rerun()
            if c2.button("❌ No, Keep Original Specs", use_container_width=True): _send("no"); st.rerun()
        elif cur == "swatch_selected":
            c1, c2 = st.columns(2)
            if c1.button("🚀 Confirm Order & Place", use_container_width=True): _send("confirm"); st.rerun()
            if c2.button("⬅️ Back to Selection", use_container_width=True): _send("back"); st.rerun()
        elif cur in ("confirmed", "failed"):
            if st.button("✨ Start New Saree Search", use_container_width=True):
                for k in list(st.session_state.keys()):
                    if k not in ("one_of_a_kind", "buyer_orders", "weaver_orders", "weaver_id", "min_base_price", "audio_work_mode", "custom_weavers"):
                        del st.session_state[k]
                st.rerun()
        else:
            if cur == "greeting" and not st.session_state["history"] and not st.session_state["greeted"]:
                st.session_state["greeted"] = True; _send("hi"); st.rerun()

            st.markdown('<div class="section-label">🎙️ Speak Your Request (बोलकर बताएं)</div>', unsafe_allow_html=True)
            audio_file = st.audio_input("Record", label_visibility="collapsed", key=f"pakshi_audio_{st.session_state['audio_counter']}")
            if audio_file is not None:
                with st.spinner("🎧 Transcribing..."):
                    text, err = _transcribe_audio(audio_file)
                st.session_state["audio_counter"] += 1
                if err: st.warning(err); st.rerun()
                else:
                    t = text.lower().strip()
                    nmap = {"one":"1", "two":"2", "three":"3", "first":"1", "second":"2", "third":"3", "ek":"1", "do":"2", "teen":"3", "pehla":"1", "doosra":"2", "teesra":"3"}
                    if t in nmap and cur == "retrieved": _send(nmap[t])
                    elif _is_correction(t) and cur == "retrieved": _send(t, force_new_search=True)
                    else: _send(text)
                    st.rerun()

            prefill = st.session_state.pop("prefill_text", "")
            ui = st.text_input("Msg", value=prefill, placeholder="Type your message...", label_visibility="collapsed", key=f"txt_{len(st.session_state['history'])}")
            if st.button("📤 Send", key="send_btn", use_container_width=True) and ui.strip():
                if cur == "retrieved" and not _is_number_selection(ui.strip()): _send(ui.strip(), force_new_search=True)
                else: _send(ui.strip())
                st.rerun()

# ---------------------------------------------------------------------------
# WEAVER PAGE (Voice Router + Min Base Price)
# ---------------------------------------------------------------------------
def _weaver_page() -> None:
    _init_weaver_state()
    all_weavers = _get_all_weavers()  # ← now includes custom weavers
    st.markdown('<div class="section-label">🧑‍🎨 Artisan Portal (बुनकर पोर्टल)</div>', unsafe_allow_html=True)

    col_sel, col_stat = st.columns([2, 3])
    with col_sel:
        # Build dropdown from ALL weavers (built-in + custom)
        opts = [f"{w['id']} — {w.get('name','Unknown')} ({w.get('cluster','')})" for w in all_weavers]
        if not opts:
            opts = ["No weavers registered. Please onboard."]
        selected = st.selectbox("Logged in as (प्रोफाइल)", opts, key="weaver_select")
        if selected and " — " in selected:
            st.session_state["weaver_id"] = selected.split(" — ")[0]
        else:
            st.session_state["weaver_id"] = None

    current_id = st.session_state.get("weaver_id")
    profile = next((w for w in all_weavers if w.get("id") == current_id), {})
    if not profile:
        st.warning("Please select a valid weaver profile or register as a new weaver.")
        return

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    c_base, c_audio = st.columns([2, 2], gap="large")
    with c_base:
        st.markdown("**🛡️ Minimum Base Price Threshold**")
        st.session_state["min_base_price"] = st.number_input("Min Base Price (₹)", min_value=500, max_value=15000, step=100, value=st.session_state["min_base_price"], label_visibility="collapsed")
    with c_audio:
        st.markdown("**🔊 Hands-Free Loom Audio Mode**")
        st.session_state["audio_work_mode"] = st.toggle("Enable Hindi Announcements", value=st.session_state["audio_work_mode"])

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # ── Voice Router for Weavers ──
    st.markdown('<div class="section-label">🎙️ Voice Loom Controls (हाथों के बिना काम करें)</div>', unsafe_allow_html=True)
    st.caption("Say 'Pehla order swikaar karo' (Accept first), 'Order 2847 mana karo' (Reject), or 'Buyer ko dikhao' (Send photo to buyer).")

    w_audio = st.audio_input("Record Weaver Command", label_visibility="collapsed", key=f"w_audio_{st.session_state['weaver_audio_counter']}")

    orders = st.session_state["weaver_orders"]
    pending = [o for o in orders if o.get("status") == "pending"]
    accepted = [o for o in orders if o.get("status") == "accepted"]

    if w_audio is not None:
        with st.spinner("🎧 Sun rahe hain..."):
            text, err = _transcribe_audio(w_audio)
        st.session_state["weaver_audio_counter"] += 1

        if err:
            st.warning(err)
        else:
            st.info(f'🗣️ Heard: "{text}"')
            cmd = _parse_weaver_voice_command(text, pending, accepted)

            if cmd and cmd.get("action") != "error":
                act, oid = cmd["action"], cmd["order_id"]
                # Find index in global orders
                idx = next((i for i, o in enumerate(orders) if o["order_id"] == oid), None)
                if idx is not None:
                    if act == "accept":
                        orders[idx]["status"] = "accepted"
                        # Update buyer orders as well
                        for bo in st.session_state.get("buyer_orders", []):
                            if bo["order_id"] == oid:
                                bo["status"] = "In Production"
                        st.session_state["weaver_orders"] = orders  # force update
                        hi_txt = f"Order {oid[-4:]} swikaar ho gaya. Loom par bhej diya."
                        if ab := _tts_bytes(hi_txt, lang="hi"):
                            _autoplay_audio(ab)
                        st.success(f"✅ Voice Command: Accepted {oid}!")
                        st.rerun()

                    elif act == "decline":
                        orders[idx]["status"] = "declined"
                        st.session_state["weaver_orders"] = orders
                        hi_txt = f"Order {oid[-4:]} mana kar diya gaya."
                        if ab := _tts_bytes(hi_txt, lang="hi"):
                            _autoplay_audio(ab)
                        st.warning(f"❌ Voice Command: Declined {oid}.")
                        st.rerun()

                    elif act == "show_buyer":
                        orders[idx]["status"] = "awaiting_approval"
                        orders[idx]["photo"] = "loom_snapshot_auto.jpg"
                        st.session_state["weaver_orders"] = orders
                        # Update buyer side
                        for bo in st.session_state.get("buyer_orders", []):
                            if bo["order_id"] == oid:
                                bo["status"] = "Awaiting Approval"
                                bo["photo_path"] = "loom_snapshot_auto.jpg"
                        hi_txt = f"Fabric tayyar hai. Buyer ko tasveer bhej di gayi hai."
                        if ab := _tts_bytes(hi_txt, lang="hi"):
                            _autoplay_audio(ab)
                        st.success(f"📸 Voice Command: Photo sent to buyer for {oid}. Awaiting Approval.")
                        st.rerun()
                else:
                    st.error(f"Order {oid} not found.")
            else:
                msg = cmd["message"] if cmd else "Command not recognised."
                st.warning(msg)
                st.caption("Try: 'pehla order swikaar karo' / 'accept first order' / 'order 2847 mana karo'")

    # ── Display Order Queues ──
    if st.session_state.get("audio_work_mode") and (pending or accepted):
        if st.button("Read My Orders Aloud", use_container_width=False, key="read_orders_btn"):
            lines = []
            if pending:
                lines.append(f"Aapke paas {len(pending)} naye order hain.")
                for o in pending[:3]:
                    lines.append(
                        f"Order {o.get('order_id','')[-4:]}: "
                        f"{o.get('weave_style','fabric')}, "
                        f"{o.get('color','')}, "
                        f"keemat {o.get('price',0)} rupaye, "
                        f"deliver by {o.get('delivery_by','')}."
                    )
            if accepted:
                lines.append(f"{len(accepted)} order loom par chal rahe hain.")
            full_text = " ".join(lines)
            if ab := _tts_bytes(full_text, lang="hi"):
                _autoplay_audio(ab, label="Your orders summary")
            else:
                st.warning("Audio unavailable — check edge-tts is installed.")

    if pending:
        st.markdown('<div class="section-label" style="margin-top:1rem;">📥 Pending Broadcasts</div>', unsafe_allow_html=True)
        for order in pending:
            idx = next((i for i, o in enumerate(orders) if o.get("order_id") == order.get("order_id")), None)
            is_below = int(order.get("price",0)) < st.session_state["min_base_price"]
            bg_card = "order-card below-base" if is_below else "order-card"
            badge = f'<span class="tag-warning">⚠️ Below Base (₹{st.session_state["min_base_price"]})</span>' if is_below else '<span class="tag">✓ Meets Base</span>'

            st.markdown(f"""
            <div class="{bg_card}">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div><div style="font-weight:800;font-size:1.05rem;color:var(--text-white);">{order.get("weave_style","—")}</div>
                         <div style="font-size:0.80rem;color:var(--text-muted);">#{order.get("order_id","—")} · {badge}</div></div>
                    <div class="swatch-price">₹{order.get("price",0):,}</div>
                </div>
            </div>""", unsafe_allow_html=True)

            b1, b2 = st.columns(2)
            if b1.button("✅ Accept", key=f"acc_{order['order_id']}", use_container_width=True):
                orders[idx]["status"] = "accepted"
                st.session_state["weaver_orders"] = orders
                if ab := _tts_bytes("Order swikaar kiya", lang="hi"): _autoplay_audio(ab)
                st.rerun()
            if b2.button("❌ Decline", key=f"dec_{order['order_id']}", use_container_width=True):
                orders[idx]["status"] = "declined"
                st.session_state["weaver_orders"] = orders
                st.rerun()

    if accepted:
        st.markdown('<div class="section-label" style="margin-top:1rem;">🧵 In Production (लूम पर)</div>', unsafe_allow_html=True)
        for order in accepted:
            idx = next((i for i, o in enumerate(orders) if o.get("order_id") == order.get("order_id")), None)
            st.markdown(f"""
            <div class="order-card accepted">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div><div style="font-weight:700;font-size:0.95rem;color:var(--text-white);">{order.get("weave_style","—")}</div>
                         <div style="font-size:0.80rem;color:var(--text-muted);">#{order.get("order_id","—")}</div></div>
                    <div class="state-badge state-active">In Production</div>
                </div>
            </div>""", unsafe_allow_html=True)

            uploaded = st.file_uploader(
                f"Upload progress photo — #{order['order_id']}",
                type=["jpg","jpeg","png"],
                key=f"photo_{order['order_id']}",
                label_visibility="collapsed",
            )
            if uploaded:
                st.image(uploaded, caption=f"Progress photo — {order['order_id']}", width=260)
            if st.button(f"Send Photo for Buyer Approval — #{order['order_id']}", key=f"show_{order['order_id']}"):
                photo_name = uploaded.name if uploaded else "loom_snapshot.jpg"
                orders[idx]["status"] = "awaiting_approval"
                orders[idx]["photo"] = photo_name
                st.session_state["weaver_orders"] = orders
                for bo in st.session_state.get("buyer_orders", []):
                    if bo["order_id"] == order["order_id"]:
                        bo["status"] = "Photo Sent — Awaiting Approval"
                        bo["photo_path"] = photo_name
                st.success(f"Photo sent for #{order['order_id']}. Buyer will be notified.")
                st.rerun()

    awaiting = [o for o in orders if o.get("status") == "awaiting_approval"]
    if awaiting:
        st.markdown('<div class="section-label" style="margin-top:1rem;">⏳ Awaiting Buyer Approval</div>', unsafe_allow_html=True)
        for order in awaiting:
            st.info(f"Order #{order['order_id']} is pending approval from the buyer on Meesho.")

    st.markdown('<div style="height:1.2rem;"></div>', unsafe_allow_html=True)
    if st.button("📡 Simulate New Incoming Broadcast", use_container_width=True):
        # Use the current profile's specialty to generate a matching order
        specialty = profile.get("weave_style", "Handloom")
        weave_map = {
            "Ikat": ("Pochampally Ikat", "Cotton-Silk"),
            "Banarasi": ("Banarasi Brocade", "Silk"),
            "Block Print": ("Block Print", "Cotton"),
            "Kanjivaram": ("Kanjivaram Silk", "Silk"),
            "Tussar": ("Tussar", "Silk"),
            "Chanderi": ("Chanderi", "Cotton-Silk"),
            "Paithani": ("Paithani", "Silk"),
            "Patola": ("Patola", "Silk"),
        }
        weave_style, fabric_type = "Handloom", "Cotton"
        for key, (w, f) in weave_map.items():
            if key.lower() in specialty.lower():
                weave_style, fabric_type = w, f
                break

        new_order = {
            "order_id": f"PKS-{random.randint(2900, 2999)}",
            "fabric": fabric_type,
            "weave_style": weave_style,
            "color": random.choice(["Maroon", "Teal", "Mustard Yellow", "Ivory", "Navy Blue", "Deep Red"]),
            "occasion": random.choice(["Wedding", "Festival", "Casual", "Office"]),
            "buyer_feel": random.choice(["royal, heavy", "light, airy", "elegant", "comfortable"]),
            "price": random.choice([800, 1200, 1800, 2500, 3500, 5000]),
            "delivery_by": "July 28, 2026",
            "status": "pending",
            "photo": None,
            "buyer_note": f"Direct voice broadcast matching your {specialty} specialty.",
            "weaver_location": profile.get("cluster", "India"),
        }
        st.session_state["weaver_orders"].insert(0, new_order)
        if st.session_state["audio_work_mode"]:
            if ab := _tts_bytes(f"Naya order aaya hai! Keemat {new_order['price']} rupaye.", lang="hi"):
                _autoplay_audio(ab)
        st.rerun()

# ---------------------------------------------------------------------------
# ONE OF A KIND PAGE (Wholesale Resale Outlet)
# ---------------------------------------------------------------------------
_OOAK_SEED = [
    {
        "order_id": "PKS-2801",
        "weave_style": "Pochampally Ikat",
        "color": "Teal with gold border",
        "original_price": 1800,
        "resale_price": 1080,
        "weaver_name": "Padmavathi Devi",
        "weaver_cluster": "Pochampally",
        "weaver_state": "Telangana",
        "sensory_tags": ["flowy", "breathable yet elegant", "light but rich"],
        "reason": "Colour slightly deeper than buyer expected",
    },
    {
        "order_id": "PKS-2788",
        "weave_style": "Chanderi Cotton Silk",
        "color": "Ivory with silver zari",
        "original_price": 2400,
        "resale_price": 1440,
        "weaver_name": "Kamla Bai",
        "weaver_cluster": "Chanderi",
        "weaver_state": "Madhya Pradesh",
        "sensory_tags": ["sheer", "elegant", "soft sheen"],
        "reason": "Weaving imperfection on pallu border",
    },
]

def _ooak_page() -> None:
    st.markdown('<div class="section-label">♻️ One of a Kind — Wholesale Resale Outlet</div>', unsafe_allow_html=True)

    # Seed demo items on first visit so page is never empty for judges
    if "ooak_seeded" not in st.session_state:
        existing_ids = {i.get("order_id") for i in st.session_state.get("one_of_a_kind", [])}
        for seed in _OOAK_SEED:
            if seed["order_id"] not in existing_ids:
                st.session_state.setdefault("one_of_a_kind", []).append(seed)
        st.session_state["ooak_seeded"] = True

    items = st.session_state.get("one_of_a_kind", [])
    if not items:
        st.markdown("""
        <div class="card" style="text-align:center;padding:2rem;">
            <div style="font-size:0.95rem;font-weight:700;margin-bottom:0.4rem;">No rejected pieces yet — that is a good sign</div>
            <div style="font-size:0.82rem;color:var(--text-muted);">When a custom order does not meet a buyer's expectation,
            it lands here at wholesale price. No waste. No loss.</div>
        </div>""", unsafe_allow_html=True)
        return

    st.caption(f"{len(items)} unique handwoven piece{'s' if len(items)>1 else ''} at wholesale prices — ready to ship.")

    for idx, item in enumerate(items):
        orig, resale = item.get("original_price", 0), item.get("resale_price", 0)
        discount = int((1 - resale / orig) * 100) if orig else 0
        tags_html = "".join(
            f'<span class="tag">{t}</span>'
            for t in item.get("sensory_tags", [])[:3]
        )
        col_card, col_btn = st.columns([5, 1], gap="small")
        with col_card:
            st.markdown(f"""
            <div class="card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;">
                    <div>
                        <div style="font-weight:800;font-size:1.05rem;color:var(--text-white);">
                            {item.get("weave_style","—")} &middot; {item.get("color","—")}
                        </div>
                        <div style="font-size:0.78rem;color:var(--text-muted);margin-top:2px;">
                            #{item.get("order_id","—")} &middot; {item.get("reason","Rejected custom piece")}
                        </div>
                        <div style="font-size:0.78rem;color:var(--text-muted);margin-top:2px;">
                            Woven by <strong style="color:var(--text-primary);">{item.get("weaver_name","—")}</strong>
                            &middot; {item.get("weaver_cluster","—")}, {item.get("weaver_state","—")}
                        </div>
                        <div style="margin-top:6px;">{tags_html}
                            <span class="tag" style="background:rgba(34,197,94,0.15);color:#22c55e;">ready to ship</span>
                        </div>
                    </div>
                    <div style="text-align:right;flex-shrink:0;">
                        <div style="font-size:0.78rem;color:var(--text-muted);text-decoration:line-through;">₹{orig:,}</div>
                        <div class="swatch-price">₹{resale:,}</div>
                        <div style="background:rgba(34,197,94,0.2);color:#22c55e;padding:2px 8px;
                            border-radius:999px;font-size:0.72rem;font-weight:700;display:inline-block;margin-top:2px;">
                            {discount}% off
                        </div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
        with col_btn:
            st.markdown('<div style="height:1.2rem;"></div>', unsafe_allow_html=True)
            if st.button("Buy Now", key=f"buy_{item.get('order_id',idx)}_{idx}", use_container_width=True):
                st.success(f"#{item.get('order_id','')} added to cart. Delivery in 3-5 days.")

# ---------------------------------------------------------------------------
# WEAVER ONBOARDING PAGE (Now persists profiles)
# ---------------------------------------------------------------------------
def _onboarding_page() -> None:
    st.markdown('<div class="section-label">Weaver Onboarding — Join the Pakshi Network</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background:rgba(245,166,35,0.08);border:1px solid rgba(245,166,35,0.25);
        border-radius:10px;padding:0.75rem 1rem;margin-bottom:1rem;font-size:0.82rem;
        color:var(--text-primary);line-height:1.6;">
        <strong style="color:#f5a623;">Powered by Meesho</strong> — Once you complete onboarding,
        your weaver profile goes live on the Pakshi network. Buyers describe what they want,
        the agent matches you, and orders come directly to your phone. No middlemen.
        Your craft. Your price.
    </div>
    """, unsafe_allow_html=True)

    if "onboard_submitted" not in st.session_state:
        st.session_state["onboard_submitted"] = False
    if "onboard_data" not in st.session_state:
        st.session_state["onboard_data"] = {}

    if st.session_state["onboard_submitted"]:
        d = st.session_state["onboard_data"]
        # New weaver is already stored, show success and invite to dashboard
        st.markdown(f"""
        <div style="background:rgba(34,197,94,0.08);border:1.5px solid #22c55e;
            border-radius:12px;padding:1.4rem;text-align:center;margin-top:1rem;">
            <div style="font-size:1.3rem;font-weight:800;color:#22c55e;margin-bottom:0.4rem;">
                ✅ Profile Live!
            </div>
            <div style="font-size:0.85rem;color:var(--text-primary);line-height:1.7;">
                Welcome to Pakshi, <strong>{d.get("name","")}</strong>.<br>
                Cluster: {d.get("cluster","")} · Speciality: {d.get("fabric","")}<br>
                Your profile is now active. Switch to the <strong>Weaver Dashboard</strong> tab
                to view your orders.<br>
                <span style="color:#f5a623;font-weight:600;">
                Meesho Seller ID will be sent to {d.get("phone","")} via WhatsApp.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Go to Weaver Dashboard", use_container_width=True):
            # Auto-select the new weaver (already set in session state)
            st.session_state["onboard_submitted"] = False
            st.session_state["onboard_data"] = {}
            # Rerun to switch to the dashboard tab – we'll do it via navigation
            st.success("Navigating to Dashboard...")
            # We'll force the tab to switch by setting a query param
            st.query_params.update({"tab": "Weaver Dashboard"})
            st.rerun()
        if st.button("Register Another Weaver", use_container_width=True):
            st.session_state["onboard_submitted"] = False
            st.session_state["onboard_data"] = {}
            st.rerun()
        return

    with st.form("onboard_form"):
        st.markdown('<div class="section-label">Basic Details</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        name     = c1.text_input("Full Name (पूरा नाम)", placeholder="e.g. Padmavathi Devi")
        phone    = c2.text_input("Mobile / WhatsApp Number", placeholder="10-digit number")

        c3, c4 = st.columns(2)
        cluster  = c3.text_input("Village / Cluster (गांव / क्लस्टर)", placeholder="e.g. Pochampally")
        state    = c4.selectbox("State (राज्य)", [
            "Andhra Pradesh", "Bihar", "Gujarat", "Jharkhand", "Karnataka",
            "Kerala", "Madhya Pradesh", "Maharashtra", "Odisha", "Rajasthan",
            "Tamil Nadu", "Telangana", "Uttar Pradesh", "West Bengal", "Other"
        ])

        st.markdown('<div class="section-label" style="margin-top:0.8rem;">Craft Details</div>', unsafe_allow_html=True)
        c5, c6 = st.columns(2)
        fabric   = c5.multiselect("Fabric Speciality", ["Cotton", "Silk", "Cotton-Silk", "Tussar", "Linen"])
        weave    = c6.text_input("Weave Style (बुनाई शैली)", placeholder="e.g. Ikat, Jamdani, Block Print")

        c7, c8 = st.columns(2)
        min_p    = c7.number_input("Minimum Order Price (₹)", min_value=300, max_value=50000, value=1000, step=100)
        delivery = c8.number_input("Typical Delivery Days", min_value=3, max_value=60, value=14, step=1)

        st.markdown('<div class="section-label" style="margin-top:0.8rem;">Verification</div>', unsafe_allow_html=True)
        c9, c10 = st.columns(2)
        aadhaar  = c9.text_input("Aadhaar Last 4 Digits", placeholder="XXXX", max_chars=4)
        bank     = c10.text_input("Bank Account Number (for payments)", placeholder="Account number")

        whatsapp = st.checkbox("I have WhatsApp on this number and can receive order notifications")
        custom   = st.checkbox("I can accept custom / made-to-order requests")
        consent  = st.checkbox("I agree to list on Meesho through the Pakshi network")

        lang     = st.selectbox("Preferred Language for Notifications", [
            "Hindi", "Telugu", "Tamil", "Kannada", "Bengali", "Gujarati", "Marathi", "English"
        ])

        photo    = st.file_uploader("Upload a sample of your work (optional)", type=["jpg","jpeg","png"])
        if photo:
            st.image(photo, caption="Sample work preview", width=260)

        submitted = st.form_submit_button("Submit Profile — Join Pakshi Network", use_container_width=True)

        if submitted:
            errors = []
            if not name.strip():       errors.append("Name is required.")
            if not phone.strip() or len(phone.strip()) != 10 or not phone.strip().isdigit():
                errors.append("Valid 10-digit mobile number is required.")
            if not cluster.strip():    errors.append("Village / Cluster is required.")
            if not fabric:             errors.append("Select at least one fabric speciality.")
            if not consent:            errors.append("You must agree to list on Meesho.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                # Create new weaver profile
                new_id = f"CW{random.randint(100,999)}"
                new_profile = {
                    "id": new_id,
                    "name": name.strip(),
                    "cluster": cluster.strip(),
                    "state": state,
                    "fabric_specialty": fabric,
                    "weave_style": weave.strip(),
                    "price_range_inr": {"min": min_p, "max": min_p * 3},
                    "rating": 4.0,
                    "orders_completed": 0,
                    "active": True,
                    "phone": phone.strip(),
                    "whatsapp": whatsapp,
                    "accepts_custom": custom,
                    "language": lang,
                }
                st.session_state.setdefault("custom_weavers", []).append(new_profile)
                st.session_state["weaver_id"] = new_id  # auto‑select

                st.session_state["onboard_data"] = {
                    "name": name.strip(), "phone": phone.strip(),
                    "cluster": cluster.strip(), "state": state,
                    "fabric": ", ".join(fabric), "weave": weave.strip(),
                    "min_price": min_p, "delivery_days": delivery,
                    "whatsapp": whatsapp, "accepts_custom": custom,
                    "language": lang,
                }
                st.session_state["onboard_submitted"] = True
                st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    _render_header()

    if "app_loaded" not in st.session_state:
        st.markdown(
            '<div style="background:rgba(218,65,103,0.1);border:1px solid rgba(218,65,103,0.3);'
            'border-radius:8px;padding:0.5rem 1rem;font-size:0.82rem;color:#f0bcd4;'
            'margin-bottom:0.8rem;">Agent is warming up on first load — this takes about '
            '15 seconds. Subsequent responses will be instant.</div>',
            unsafe_allow_html=True,
        )
        st.session_state["app_loaded"] = True

    # Read tab from query param to allow navigation after onboarding
    default_tab = 0
    tab_param = st.query_params.get("tab")
    if tab_param:
        if "Buyer" in tab_param:
            default_tab = 0
        elif "Weaver Dashboard" in tab_param:
            default_tab = 1
        elif "Wholesale Resale" in tab_param:
            default_tab = 2
        elif "Weaver Onboarding" in tab_param:
            default_tab = 3
        # Clear param after reading
        st.query_params.clear()

    tab = st.radio(
        "Nav",
        ["Buyer Portal", "Weaver Dashboard", "Wholesale Resale", "Weaver Onboarding"],
        horizontal=True,
        label_visibility="collapsed",
        index=default_tab,
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    if "Buyer" in tab: _buyer_page()
    elif "Weaver Dashboard" in tab: _weaver_page()
    elif "Onboarding" in tab: _onboarding_page()
    else: _ooak_page()

if __name__ == "__main__":
    main()
