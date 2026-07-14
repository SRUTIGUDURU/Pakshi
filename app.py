"""
Pakshi - Full Streamlit App
============================
Buyer  : describe your saree -> agent finds swatches -> confirm order
Weaver : see incoming orders -> accept/decline -> upload progress photo
OOAK   : rejected pieces listed at wholesale price

Run:
    pip install streamlit chromadb scikit-learn edge-tts edge-stt
    streamlit run app.py

Same-directory files required:
    agent.py, intent_parser.py, retrieval.py, setup_chromadb.py,
    fabric_ontology.json, fabric_swatches.json, weaver_profiles.json
"""

import base64
import json
import os
import random
import tempfile
import time
import asyncio
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
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
    --accent:         #da4167;
    --accent-hover:   #b22f72;
    --text-primary:   #f0bcd4;
    --text-muted:     #bdada6;
    --text-white:     #ffffff;
    --success:        #22c55e;
    --danger:         #ef4444;
    --border:         rgba(240,188,212,0.12);
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: var(--bg-deep);
    color: var(--text-primary);
}
.main  { background-color: var(--bg-deep); }
.block-container { padding: 1.5rem 2rem 3rem; max-width: 1100px; }
#MainMenu, footer, header { visibility: hidden; }

.wordmark {
    font-size: 2rem; font-weight: 800;
    color: var(--text-white); letter-spacing: -0.5px;
}
.wordmark span { color: var(--accent); }
.tagline { font-size: 0.85rem; color: var(--text-muted); margin-top: -4px; margin-bottom: 1.5rem; }

.card {
    background: rgba(58,24,112,0.6);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    color: var(--text-primary);
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }

.swatch-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px; padding: 1rem; height: 100%;
}
.swatch-price { font-size: 1.4rem; font-weight: 800; color: var(--accent); }
.swatch-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.swatch-value { font-size: 0.9rem; font-weight: 500; color: var(--text-white); }
.tag {
    display: inline-block; padding: 2px 8px; border-radius: 999px;
    background: rgba(218,65,103,0.15); color: var(--accent);
    font-size: 0.72rem; font-weight: 500; margin: 2px 2px 0 0;
}

.bubble-agent {
    background: var(--bg-surface); border: 1px solid var(--border);
    border-radius: 12px 12px 12px 2px; padding: 0.75rem 1rem;
    margin: 0.4rem 0; max-width: 82%; font-size: 0.9rem;
    line-height: 1.55; white-space: pre-wrap; color: var(--text-primary);
}
.bubble-user {
    background: var(--bg-card); border-radius: 12px 12px 2px 12px;
    padding: 0.75rem 1rem; margin: 0.4rem 0 0.4rem auto;
    max-width: 70%; font-size: 0.9rem; line-height: 1.55;
    text-align: right; color: var(--text-white);
}

.section-label {
    font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: var(--accent); margin-bottom: 0.4rem;
}

.confirmed-banner {
    background: linear-gradient(135deg,rgba(34,197,94,0.13),rgba(34,197,94,0.04));
    border: 1.5px solid #22c55e; border-radius: 12px;
    padding: 1.4rem; text-align: center; margin-top: 1rem;
}
.confirmed-banner h2 { color: #22c55e; margin: 0; font-size: 1.5rem; }

.order-card {
    background: var(--bg-surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.8rem;
}
.order-card.accepted { border-color: rgba(34,197,94,0.3); }
.order-card.declined { border-color: rgba(239,68,68,0.3); opacity: 0.6; }

.state-badge {
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; margin-bottom: 0.6rem;
}
.state-active  { background: rgba(34,197,94,0.2);  color: #22c55e; }
.state-pending { background: rgba(218,65,103,0.2); color: var(--accent); }

.reasoning-box {
    background: rgba(218,65,103,0.08); border-left: 3px solid var(--accent);
    border-radius: 0 8px 8px 0; padding: 0.75rem 1rem;
    font-size: 0.82rem; color: var(--text-muted);
    font-style: italic; line-height: 1.6; margin: 0.6rem 0;
}

.step-row { display: flex; align-items: center; gap: 0.6rem; margin: 0.3rem 0; font-size: 0.85rem; }
.step-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.step-dot.done    { background: #22c55e; }
.step-dot.active  { background: var(--accent); }
.step-dot.pending { background: var(--bg-card); opacity: 0.4; }

.divider { height: 1px; background: var(--border); margin: 1.2rem 0; }

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
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(218,65,103,0.25) !important;
}

.stButton > button {
    background: var(--accent) !important; color: var(--text-white) !important;
    font-weight: 700 !important; border: none !important;
    border-radius: 8px !important; padding: 0.5rem 1.4rem !important;
    font-family: 'Inter', sans-serif !important; transition: opacity 0.15s;
}
.stButton > button:hover { opacity: 0.88 !important; box-shadow: 0 0 16px rgba(218,65,103,0.4) !important; }

.stRadio > div { gap: 0.4rem; }
.stRadio label { font-size: 0.88rem !important; color: var(--text-primary) !important; }
.stSelectbox > div > div {
    background-color: var(--bg-surface) !important;
    color: var(--text-white) !important;
    border: 1.5px solid var(--bg-card) !important;
    border-radius: 8px !important;
}
.streamlit-expanderHeader { color: var(--accent) !important; font-weight: 600 !important; }
.streamlit-expanderContent { background: var(--bg-surface) !important; border-radius: 0 0 8px 8px !important; }
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
# Edge TTS (Text-to-Speech) — Completely Free, No API Key
# ---------------------------------------------------------------------------
_EDGE_TTS_VOICES = {
    "te": "te-IN-MohanNeural",      # Telugu
    "ta": "ta-IN-ValluvarNeural",   # Tamil
    "kn": "kn-IN-GaganNeural",      # Kannada
    "hi": "hi-IN-MadhurNeural",     # Hindi
    "bn": "bn-IN-TanishaaNeural",   # Bengali
    "or": "or-IN-SambitNeural",     # Odia
    "en": "en-IN-PrabhatNeural",    # English (Indian accent)
}


def _tts_edge(text: str, lang: str = "te") -> bytes | None:
    """
    Convert text to speech using Edge TTS (Microsoft Edge voices).
    Completely free, no API key required.
    """
    if not text:
        return None

    voice = _EDGE_TTS_VOICES.get(lang, "hi-IN-MadhurNeural")

    # Trim text to avoid issues with very long text
    spoken = ". ".join(text.split(". ")[:2]).strip()
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

        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tmp_path = loop.run_until_complete(generate())
        loop.close()

        # Read the file
        with open(tmp_path, "rb") as f:
            data = f.read()

        # Clean up
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

        return data

    except Exception as e:
        print(f"Edge TTS error: {e}")
        return None


def _tts_bytes(text: str, lang: str = "en") -> bytes | None:
    """Main TTS entry point — uses Edge TTS."""
    if not text:
        return None
    return _tts_edge(text, lang)


def _autoplay_audio(audio_bytes: bytes, fmt: str = "mp3") -> None:
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(
        f'<audio autoplay style="display:none">'
        f'<source src="data:audio/{fmt};base64,{b64}" type="audio/{fmt}">'
        f'</audio>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Edge STT (Speech-to-Text) — Completely Free, No API Key
# ---------------------------------------------------------------------------
def _stt_edge(audio_bytes: bytes) -> tuple:
    """
    Transcribe audio using Edge STT (Microsoft Azure Speech SDK free tier).
    Completely free, no API key required for basic usage.
    """
    if len(audio_bytes) < 8_000:
        return None, "Recording too short. Speak clearly for at least 2 seconds."

    # Map of language codes for Edge STT
    lang_map = {
        "te": "te-IN", "ta": "ta-IN", "kn": "kn-IN",
        "hi": "hi-IN", "bn": "bn-IN", "or": "or-IN",
        "en": "en-IN"
    }

    # Try to detect language from the audio (simplified)
    # For Edge STT, we need to try each language until one works
    # We'll default to auto-detect with the built-in SpeechRecognizer

    try:
        # Edge STT is available through the Edge browser's Speech Recognition API
        # Since we're in a server environment, we use a workaround:
        # We'll use the speech_recognition library with Azure's free tier
        # OR we can use the built-in whisper as fallback
        import speech_recognition as sr

        recognizer = sr.Recognizer()

        # Save audio to a temporary WAV file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with sr.AudioFile(tmp_path) as source:
            audio = recognizer.record(source)

        # Try to recognize with Google Web Speech API (free, no key)
        # This works well for Indian languages
        try:
            # Try with language hints for Indian languages
            for lang_code in [lang_map.get("hi", "hi-IN"), lang_map.get("te", "te-IN"),
                              lang_map.get("ta", "ta-IN"), lang_map.get("kn", "kn-IN"),
                              lang_map.get("bn", "bn-IN"), "en-IN"]:
                try:
                    text = recognizer.recognize_google(audio, language=lang_code)
                    if text and len(text) > 2:
                        return text, None
                except:
                    continue

            # If all language-specific attempts fail, try default
            text = recognizer.recognize_google(audio)
            if text and len(text) > 2:
                return text, None

            return None, "Could not understand. Please try again."

        except sr.UnknownValueError:
            return None, "Could not understand audio. Please try again."
        except sr.RequestError as e:
            # Fallback: If Google STT fails, try to return a useful error
            print(f"Google STT error: {e}")
            return None, "Speech recognition service unavailable. Please type your request."
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    except ImportError:
        # If speech_recognition is not installed, use whisper as fallback
        try:
            import whisper

            @st.cache_resource(show_spinner=False)
            def _load_whisper():
                return whisper.load_model("base")

            model = _load_whisper()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            result = model.transcribe(tmp_path, language="hi", fp16=False)

            try:
                os.unlink(tmp_path)
            except OSError:
                pass

            text = result.get("text", "").strip()
            if text and len(text) > 2:
                return text, None
            return None, "Could not understand. Please try again."

        except Exception as e:
            return None, f"Speech recognition unavailable: {e}"

    except Exception as e:
        return None, f"Speech recognition error: {e}"


def _transcribe_audio(audio_file) -> tuple:
    """
    Transcribe a Streamlit audio_input file object.
    Returns (transcribed_text, error_message)
    """
    buf = audio_file.getbuffer()
    return _stt_edge(buf)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def _init_buyer_state() -> None:
    defaults = {
        "agent":            None,
        "history":          [],
        "current_state":    "greeting",
        "swatches":         [],
        "selected_swatch":  None,
        "order":            None,
        "agent_data":       {},
        "awaiting":         None,
        "reasoning_log":    [],
        "one_of_a_kind":    [],
        "buyer_orders":     [],
        "agent_thinking":   False,
        "audio_processed":  False,
        "prefill_text":     "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _init_weaver_state() -> None:
    if "weaver_orders" not in st.session_state:
        st.session_state["weaver_orders"] = _make_demo_orders()
    if "weaver_id" not in st.session_state:
        st.session_state["weaver_id"] = "W001"


def _make_demo_orders() -> list:
    return [
        {
            "order_id":    "PKS-2847",
            "fabric":      "Cotton-Silk",
            "weave_style": "Pochampally Ikat",
            "color":       "Teal with gold border",
            "occasion":    "Summer Wedding",
            "buyer_feel":  "flowy, breathable yet elegant",
            "price":       1800,
            "delivery_by": "July 26, 2026",
            "status":      "pending",
            "photo":       None,
            "buyer_note":  "Light saree, summer wedding, Rs.1500 - agent proposed Cotton-Silk at Rs.1800",
        },
        {
            "order_id":    "PKS-2831",
            "fabric":      "Cotton",
            "weave_style": "Pochampally Ikat",
            "color":       "Navy blue",
            "occasion":    "Office / Daily Wear",
            "buyer_feel":  "breathable, cool, non-itchy",
            "price":       750,
            "delivery_by": "July 20, 2026",
            "status":      "accepted",
            "photo":       None,
            "buyer_note":  "Office wear, breathable cotton under Rs.800",
        },
        {
            "order_id":    "PKS-2819",
            "fabric":      "Silk",
            "weave_style": "Pochampally Ikat",
            "color":       "Deep red with zari",
            "occasion":    "Wedding Reception",
            "buyer_feel":  "royal, heavy, grand",
            "price":       4200,
            "delivery_by": "August 2, 2026",
            "status":      "pending",
            "photo":       None,
            "buyer_note":  "Sister's wedding reception, deep red silk, grand",
        },
    ]


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
def _render_header() -> None:
    c1, _ = st.columns([1, 3])
    with c1:
        st.markdown(
            '<div class="wordmark">Pakshi</div>'
            '<div class="tagline">Turning buyer intent into artisan opportunity</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Step indicator
# ---------------------------------------------------------------------------
_STATE_STEPS = [
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
    active = next((i for i, (k, _) in enumerate(_STATE_STEPS) if k == current), 0)
    parts = ['<div style="display:flex;gap:1.2rem;align-items:center;margin-bottom:1rem;flex-wrap:wrap;">']
    for i, (key, label) in enumerate(_STATE_STEPS):
        if key in _HIDDEN_STATES:
            continue
        cls   = "done" if i < active else ("active" if i == active else "pending")
        color = "#22c55e" if cls == "done" else ("var(--accent)" if cls == "active" else "var(--text-muted)")
        parts.append(
            f'<div class="step-row">'
            f'<div class="step-dot {cls}"></div>'
            f'<span style="font-size:0.78rem;color:{color};font-weight:500;">{label}</span>'
            f'</div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Swatch card
# ---------------------------------------------------------------------------
def _swatch_card(swatch: dict) -> None:
    tags = "".join(
        f'<span class="tag">{t}</span>'
        for t in swatch.get("sensory_tags", [])[:3]
    )
    st.markdown(f"""
    <div class="swatch-card">
        <div style="font-weight:700;font-size:0.95rem;color:var(--text-white);margin-bottom:2px;">
            {swatch.get("weave_style","—")}
        </div>
        <div style="font-size:0.82rem;color:var(--text-muted);margin-bottom:8px;">
            {swatch.get("color","—")}
        </div>
        <div class="swatch-price">Rs.{swatch.get("price_inr","?")}</div>
        <div style="margin:8px 0">{tags}</div>
        <div class="divider"></div>
        <div class="swatch-label">Weaver</div>
        <div class="swatch-value">{swatch.get("weaver_name","—")}</div>
        <div style="font-size:0.78rem;color:var(--text-muted);">
            {swatch.get("weaver_cluster","")}, {swatch.get("weaver_state","")}
        </div>
        <div style="margin-top:4px;font-size:0.82rem;color:var(--text-primary);">
            Rating: {swatch.get("weaver_rating","?")} &nbsp;·&nbsp;
            {swatch.get("delivery_days","?")} days
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Core message dispatcher
# ---------------------------------------------------------------------------
def _send(user_text: str) -> None:
    user_text = (user_text or "").strip()
    if not user_text:
        return

    PakshiAgent, err = _load_agent_class()
    if err or PakshiAgent is None:
        st.error(f"Backend not loaded: {err}. Ensure agent.py is in the same folder.")
        return

    if st.session_state.get("agent") is None:
        try:
            st.session_state["agent"] = PakshiAgent()
        except Exception as exc:
            st.error(f"Agent init failed: {exc}")
            return

    st.session_state["history"].append(("user", user_text))
    st.session_state["agent_thinking"] = True

    try:
        response = st.session_state["agent"].chat(user_text)
    except Exception as exc:
        st.session_state["agent_thinking"] = False
        st.session_state["history"].append(("agent", f"Error: {exc}. Please try again."))
        return

    st.session_state["agent_thinking"] = False

    msg   = response.get("message", "") if isinstance(response, dict) else str(response)
    state = response.get("state",   "greeting") if isinstance(response, dict) else "greeting"
    data  = response.get("data",    {})         if isinstance(response, dict) else {}

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
        entry = {
            "order_id":    raw.get("order_id",   "PKS-???"),
            "weave_style": sw.get("weave_style", "—"),
            "color":       sw.get("color",        "—"),
            "price":       sw.get("price_inr",    0),
            "weaver_name": wv.get("weaver_name", "—"),
            "status":      "In Production",
            "photo_path":  None,
        }
        existing = {o["order_id"] for o in st.session_state.get("buyer_orders", [])}
        if entry["order_id"] not in existing:
            st.session_state["buyer_orders"].append(entry)

    if state in ("fallback_pending", "broadcasting", "weaver_selected", "confirmed"):
        snippet = msg[:120] + ("..." if len(msg) > 120 else "")
        st.session_state["reasoning_log"].append(f"[{state.upper()}] {snippet}")


# ---------------------------------------------------------------------------
# BUYER PAGE
# ---------------------------------------------------------------------------
def _buyer_page() -> None:
    _init_buyer_state()

    st.markdown('<div class="section-label">Buyer</div>', unsafe_allow_html=True)

    with st.expander("How to use (Buyer)"):
        st.markdown("""
**Step 1 — Speak or type your request.**
Describe what you want in your own words, in English, Hindi, Telugu, Kannada, Odia, Bengali or Tamil.
Example: *"Light saree for summer wedding, Rs.1500, mint green."*

**Step 2 — Review swatches.**
The agent shows up to 3 matching handloom swatches with fabric, weave style, colour, price and delivery estimate.

**Step 3 — Select a swatch.**
Type 1, 2, or 3 (or click Select) to lock your choice before production begins.

**Step 4 — Confirm.**
The agent autonomously picks the best weaver by proximity and delivery history. Order placed on Meesho.

**Step 5 — Reject if needed.**
If the final piece does not meet your expectation, click Reject Piece. It moves to One of a Kind resale at wholesale price.
        """)

    if st.session_state.get("agent_thinking"):
        st.markdown(
            '<div style="background:rgba(218,65,103,0.12);border-left:3px solid var(--accent);'
            'padding:0.6rem 1rem;border-radius:0 8px 8px 0;font-size:0.85rem;'
            'color:var(--accent);margin-bottom:0.8rem;">Agent is reasoning...</div>',
            unsafe_allow_html=True,
        )

    buyer_orders = st.session_state.get("buyer_orders", [])
    if buyer_orders:
        with st.expander(f"Your Orders ({len(buyer_orders)})"):
            for bo in buyer_orders:
                status = bo.get("status", "In Production")
                color  = {"In Production": "var(--accent)", "Photo Available": "var(--bg-card)",
                          "Completed": "#22c55e"}.get(status, "var(--text-muted)")
                photo_note = (
                    '<div style="font-size:0.78rem;color:#22c55e;margin-top:4px;">Progress photo received</div>'
                    if bo.get("photo_path") else ""
                )
                st.markdown(f"""
                <div style="background:rgba(58,24,112,0.6);border:1px solid var(--border);
                    border-radius:10px;padding:0.8rem 1rem;margin-bottom:0.5rem;">
                    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
                        <div>
                            <div style="font-weight:700;font-size:0.9rem;color:var(--text-white);">
                                {bo["weave_style"]} · {bo["color"]}
                            </div>
                            <div style="font-size:0.75rem;color:var(--text-muted);">
                                #{bo["order_id"]} · {bo["weaver_name"]} · Rs.{bo["price"]:,}
                            </div>
                            {photo_note}
                        </div>
                        <div style="background:rgba(0,0,0,0.3);padding:3px 10px;border-radius:999px;
                            font-size:0.72rem;font-weight:700;color:{color};">{status}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Re-order {bo['order_id']}", key=f"reorder_{bo['order_id']}"):
                    _send(f"{bo['weave_style']}, {bo['color']}, Rs.{bo['price']}")
                    st.rerun()

    _step_indicator(st.session_state["current_state"])

    col_chat, col_panel = st.columns([3, 2], gap="large")

    # Right panel
    with col_panel:
        swatches = st.session_state["swatches"]
        if swatches:
            st.markdown('<div class="section-label">Matching Swatches</div>', unsafe_allow_html=True)
            for i, sw in enumerate(swatches[:3]):
                _swatch_card(sw)
                if st.session_state["current_state"] == "retrieved":
                    if st.button(f"Select Swatch {i + 1}", key=f"sel_{i}"):
                        _send(str(i + 1))
                        st.rerun()

        order = st.session_state["order"]
        if order and st.session_state["current_state"] == "confirmed":
            sw = order.get("selected_swatch") or {}
            wv = order.get("selected_weaver")  or {}
            st.markdown(f"""
            <div class="confirmed-banner">
                <h2>Order Confirmed</h2>
                <div style="font-size:0.82rem;color:#86efac;margin-top:4px;">#{order.get("order_id","—")}</div>
                <div style="margin-top:12px;text-align:left;">
                    <div class="swatch-label">Fabric</div>
                    <div class="swatch-value">{sw.get("weave_style","—")} · {sw.get("color","—")}</div>
                    <div class="swatch-price" style="margin:6px 0;">Rs.{sw.get("price_inr","?")}</div>
                    <div class="divider"></div>
                    <div class="swatch-label">Weaver (agent-selected)</div>
                    <div class="swatch-value">{wv.get("weaver_name","—")}</div>
                    <div style="font-size:0.78rem;color:var(--text-muted);">
                        {wv.get("weaver_cluster","")}, {wv.get("weaver_state","")} ·
                        Rating: {wv.get("weaver_rating","?")} · {wv.get("delivery_days","?")} days
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-label">Not satisfied? Reject this piece.</div>', unsafe_allow_html=True)
            st.caption(
                "If the piece does not meet your expectation, move it to One of a Kind resale. "
                "The weaver recovers partial value. You owe nothing. No waste."
            )
            if st.button("Reject Piece — Move to One of a Kind", use_container_width=True):
                cur_ord = st.session_state.get("order") or {}
                s = cur_ord.get("selected_swatch") or {}
                w = cur_ord.get("selected_weaver")  or {}
                orig   = s.get("price_inr", 0)
                resale = int(orig * 0.6)
                st.session_state.setdefault("one_of_a_kind", []).append({
                    "order_id":       cur_ord.get("order_id",    "PKS-XXXX"),
                    "weave_style":    s.get("weave_style",       "Unknown"),
                    "color":          s.get("color",              "Unknown"),
                    "original_price": orig,
                    "resale_price":   resale,
                    "weaver_name":    w.get("weaver_name",       "Unknown"),
                    "weaver_cluster": w.get("weaver_cluster",    "Unknown"),
                    "weaver_state":   w.get("weaver_state",      "Unknown"),
                    "sensory_tags":   s.get("sensory_tags",       []),
                    "reason":         "Weaving imperfection / colour mismatch",
                })
                for k in ("current_state","order","swatches","history","agent",
                          "reasoning_log","agent_data","awaiting","selected_swatch","agent_thinking"):
                    st.session_state[k] = (
                        [] if k in ("swatches","history","reasoning_log") else
                        {} if k == "agent_data" else
                        False if k == "agent_thinking" else
                        None if k in ("order","agent","awaiting","selected_swatch") else
                        "greeting"
                    )
                st.success(f"Piece moved to One of a Kind at Rs.{resale:,}. Starting fresh.")
                st.rerun()

        if st.session_state["reasoning_log"]:
            st.markdown('<div class="section-label" style="margin-top:1rem;">Agent Reasoning</div>', unsafe_allow_html=True)
            for line in st.session_state["reasoning_log"][-3:]:
                st.markdown(f'<div class="reasoning-box">{line}</div>', unsafe_allow_html=True)

    # Left panel — chat + input
    with col_chat:
        for role, text in st.session_state["history"]:
            cls = "bubble-agent" if role == "agent" else "bubble-user"
            st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
        cur = st.session_state["current_state"]

        if cur == "fallback_pending":
            st.markdown('<div class="section-label">Agent is proposing an alternative</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Yes, show alternatives", use_container_width=True):
                    _send("yes"); st.rerun()
            with c2:
                if st.button("No, wait for my budget", use_container_width=True):
                    _send("no"); st.rerun()

        elif cur == "swatch_selected":
            st.markdown('<div class="section-label">Swatch locked — confirm order?</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Confirm Order", use_container_width=True):
                    _send("confirm"); st.rerun()
            with c2:
                if st.button("Change Selection", use_container_width=True):
                    _send("back"); st.rerun()

        elif cur in ("confirmed", "failed"):
            if st.button("Start New Search"):
                ooak  = st.session_state.get("one_of_a_kind", [])
                bords = st.session_state.get("buyer_orders",  [])
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.session_state["one_of_a_kind"] = ooak
                st.session_state["buyer_orders"]  = bords
                st.session_state["app_loaded"]    = True
                st.session_state["audio_processed"] = False
                st.rerun()

        else:
            # Auto-greet
            if cur == "greeting" and not st.session_state["history"]:
                _send("hi"); st.rerun()

            # ── Voice input ──
            if not st.session_state.get("audio_processed", False):
                st.markdown('<div class="section-label">Speak your request</div>', unsafe_allow_html=True)
                st.caption("Supports: English, Hindi, Telugu, Tamil, Kannada, Bengali, Odia. Speak for 2-3 seconds.")

                audio_file = st.audio_input(
                    "Record your fabric request",
                    label_visibility="collapsed",
                    key="pakshi_audio",
                )

                if audio_file is not None:
                    st.session_state["audio_processed"] = True

                    with st.spinner("Transcribing..."):
                        text, err = _transcribe_audio(audio_file)

                    if err:
                        st.warning(err)
                        st.session_state["audio_processed"] = False
                    else:
                        st.success(f'Heard: "{text}"')
                        _send(text)
                        st.session_state["audio_processed"] = True
                        st.rerun()
            else:
                st.info("🎤 Voice request received. Type **1**, **2**, or **3** to select a swatch, or type a new message below.")

            # ── Text input ──
            st.markdown('<div class="section-label" style="margin-top:0.8rem;">Or type</div>', unsafe_allow_html=True)

            placeholders = {
                "collecting": "e.g. Light saree for summer wedding, Rs.1500, mint green...",
                "retrieved":  "Type 1, 2, or 3 to select a swatch...",
            }
            prefill    = st.session_state.pop("prefill_text", "")
            user_input = st.text_input(
                "Your message",
                value=prefill,
                placeholder=placeholders.get(cur, "Type your message..."),
                label_visibility="collapsed",
                key=f"txt_{len(st.session_state['history'])}",
            )
            if st.button("Send", key="send_btn") and user_input.strip():
                _send(user_input.strip())
                st.session_state["audio_processed"] = False
                st.rerun()

            # Example chips
            if cur in ("greeting", "collecting") and len(st.session_state["history"]) <= 1:
                st.markdown('<div style="margin-top:0.6rem;"></div>', unsafe_allow_html=True)
                st.markdown('<div class="section-label">Try saying...</div>', unsafe_allow_html=True)
                examples = [
                    "Light saree for summer wedding, Rs.1500",
                    "Shaadi ke liye flowy cotton, around Rs.2000",
                    "Something royal for reception, deep red silk, Rs.8000",
                    "Breathable office saree, Rs.700, navy blue",
                ]
                cols = st.columns(2)
                for i, ex in enumerate(examples):
                    with cols[i % 2]:
                        if st.button(ex, key=f"ex_{i}"):
                            _send(ex); st.rerun()


# ---------------------------------------------------------------------------
# WEAVER PAGE
# ---------------------------------------------------------------------------
def _weaver_page() -> None:
    _init_weaver_state()
    weavers = _load_weaver_profiles()

    st.markdown('<div class="section-label">Weaver Dashboard</div>', unsafe_allow_html=True)

    with st.expander("How to use (Weaver)"):
        st.markdown("""
**Step 1 — Select your profile.**
Use the dropdown to log in. Your cluster, speciality, rating and orders appear alongside.

**Step 2 — Review pending orders.**
New Pakshi agent broadcasts appear under Pending, showing fabric, colour, occasion, buyer description, price and deadline.

**Step 3 — Accept or decline.**
Accept to start production. Decline if you cannot fulfil it — the agent finds another weaver.

**Step 4 — Upload a progress photo.**
Once weaving starts, upload a mid-production photo. It is shared with the buyer for preview.

**Step 5 — Simulate a broadcast.**
Click Simulate New Order Broadcast to demo incoming orders in real time.
        """)

    if not weavers:
        st.warning("No weaver profiles found. Ensure weaver_profiles.json is in the same folder.")
        return

    col_sel, col_stat = st.columns([2, 3])
    with col_sel:
        options  = [f"{w['id']} — {w.get('name','Unknown')} ({w.get('cluster','')})" for w in weavers[:10]]
        selected = st.selectbox("Logged in as", options, label_visibility="collapsed")
        wid      = selected.split(" — ")[0] if selected else ""
        st.session_state["weaver_id"] = wid

    profile = next((w for w in weavers if w.get("id") == wid), {})

    with col_stat:
        if profile:
            specs = ", ".join(profile.get("fabric_specialty", [])) or "—"
            st.markdown(f"""
            <div style="display:flex;gap:1.5rem;align-items:center;padding:0.5rem 0;flex-wrap:wrap;">
                <div><div class="swatch-label">Cluster</div>
                     <div class="swatch-value" style="font-size:0.85rem;">{profile.get("cluster","—")}</div></div>
                <div><div class="swatch-label">Speciality</div>
                     <div class="swatch-value" style="font-size:0.85rem;">{specs}</div></div>
                <div><div class="swatch-label">Rating</div>
                     <div class="swatch-value" style="font-size:0.85rem;">{profile.get("rating","—")}</div></div>
                <div><div class="swatch-label">Orders done</div>
                     <div class="swatch-value" style="font-size:0.85rem;">{profile.get("orders_completed","—")}</div></div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    orders   = st.session_state["weaver_orders"]
    pending  = [o for o in orders if o.get("status") == "pending"]
    accepted = [o for o in orders if o.get("status") == "accepted"]
    declined = [o for o in orders if o.get("status") == "declined"]

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.8rem;font-weight:800;color:var(--accent);">{len(pending)}</div><div class="swatch-label">Pending</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.8rem;font-weight:800;color:#22c55e;">{len(accepted)}</div><div class="swatch-label">Accepted</div></div>', unsafe_allow_html=True)
    total = sum(o.get("price", 0) for o in accepted)
    c3.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:1.8rem;font-weight:800;color:var(--accent);">Rs.{total:,}</div><div class="swatch-label">Value in hand</div></div>', unsafe_allow_html=True)

    st.markdown('<div style="height:0.4rem;"></div>', unsafe_allow_html=True)

    if pending:
        st.markdown('<div class="section-label">New Orders — Awaiting Your Response</div>', unsafe_allow_html=True)
        for order in pending:
            idx = next((i for i, o in enumerate(orders) if o.get("order_id") == order.get("order_id")), None)
            if idx is None:
                continue

            feel_tags = "".join(
                f'<span class="tag">{t.strip()}</span>'
                for t in str(order.get("buyer_feel","")).split(",")[:4] if t.strip()
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

            b1, b2, _ = st.columns([1, 1, 3])
            with b1:
                if st.button("Accept", key=f"acc_{order['order_id']}", use_container_width=True):
                    st.session_state["weaver_orders"][idx]["status"] = "accepted"
                    summary = (
                        f"New order: {order.get('weave_style','')}, {order.get('color','')}, "
                        f"Rs.{order.get('price',0)}, due {order.get('delivery_by','')}"
                    )
                    # Use Edge TTS with appropriate language
                    # Detect language from buyer note or default to Telugu
                    lang = "te"  # default
                    note = order.get("buyer_note", "")
                    if "tamil" in note.lower() or "ta" in note.lower():
                        lang = "ta"
                    elif "kannada" in note.lower() or "kn" in note.lower():
                        lang = "kn"
                    elif "hindi" in note.lower() or "hi" in note.lower():
                        lang = "hi"
                    elif "bengali" in note.lower() or "bn" in note.lower():
                        lang = "bn"
                    elif "odia" in note.lower() or "or" in note.lower():
                        lang = "or"
                    elif "english" in note.lower() or "en" in note.lower():
                        lang = "en"
                    
                    ab = _tts_bytes(summary, lang=lang)
                    if ab:
                        _autoplay_audio(ab)
                        st.caption(f"Listen to order details ({lang})")
                    else:
                        st.info("Audio unavailable. Order accepted.")
                    st.success(f"Order {order.get('order_id','')} accepted!")
                    time.sleep(0.4)
                    st.rerun()
            with b2:
                if st.button("Decline", key=f"dec_{order['order_id']}", use_container_width=True):
                    st.session_state["weaver_orders"][idx]["status"] = "declined"
                    st.info("Declined. Agent will find another weaver.")
                    time.sleep(0.4)
                    st.rerun()

    if accepted:
        st.markdown('<div class="section-label" style="margin-top:1rem;">In Production</div>', unsafe_allow_html=True)
        for order in accepted:
            idx = next((i for i, o in enumerate(orders) if o.get("order_id") == order.get("order_id")), None)
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
                type=["jpg","jpeg","png"],
                key=f"photo_{order.get('order_id','')}",
                label_visibility="collapsed",
            )
            if uploaded is not None:
                try:
                    st.image(uploaded, caption=f"Progress: {order.get('order_id','')}", width=280)
                    st.success("Photo sent to buyer!")
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
        st.markdown('<div class="section-label" style="margin-top:1rem;color:var(--text-muted);">Declined</div>', unsafe_allow_html=True)
        for order in declined:
            st.markdown(f"""
            <div class="order-card declined">
                <span style="font-size:0.85rem;color:var(--text-primary);">
                    {order.get("weave_style","—")} · #{order.get("order_id","—")}
                </span>
                <span style="float:right;font-size:0.75rem;color:var(--text-muted);">Declined</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)
    if st.button("Simulate New Order Broadcast"):
        weave = profile.get("weave_style", "Handloom") if profile else "Handloom"
        st.session_state["weaver_orders"].insert(0, {
            "order_id":    f"PKS-{random.randint(2900, 2999)}",
            "fabric":      random.choice(["Cotton-Silk", "Cotton", "Silk"]),
            "weave_style": weave,
            "color":       random.choice(["Sage green", "Mustard yellow", "Ivory with zari", "Teal"]),
            "occasion":    random.choice(["Wedding", "Festival", "Casual"]),
            "buyer_feel":  random.choice(["light, flowy, elegant", "royal, heavy, grand", "breathable, cool"]),
            "price":       random.choice([900, 1200, 1500, 2000, 2500]),
            "delivery_by": "July 25, 2026",
            "status":      "pending",
            "photo":       None,
            "buyer_note":  "New broadcast from Pakshi agent",
        })
        st.success("New order broadcast received!")
        st.rerun()


# ---------------------------------------------------------------------------
# ONE OF A KIND PAGE
# ---------------------------------------------------------------------------
def _ooak_page() -> None:
    st.markdown('<div class="section-label">One of a Kind — Rejected Custom Pieces</div>', unsafe_allow_html=True)

    items = st.session_state.get("one_of_a_kind", [])

    if not items:
        st.markdown("""
        <div class="card" style="text-align:center;padding:2.5rem;">
            <div style="font-weight:700;font-size:1rem;color:var(--text-white);margin-bottom:0.4rem;">
                No rejected pieces yet — that is a good sign
            </div>
            <div style="font-size:0.82rem;color:var(--text-muted);line-height:1.6;">
                When a custom order is rejected, it lands here at wholesale price.<br>
                <span style="color:var(--accent);font-weight:600;">No waste. No loss. Every piece finds a buyer.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    st.caption(f"{len(items)} unique handwoven piece{'s' if len(items)>1 else ''} available at wholesale prices.")
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    for idx, item in enumerate(items):
        orig     = item.get("original_price", 0)
        resale   = item.get("resale_price",   0)
        discount = int((1 - resale / orig) * 100) if orig > 0 else 0
        tags     = "".join(f'<span class="tag">{t}</span>' for t in item.get("sensory_tags",[])[:3])

        col1, col2 = st.columns([4, 1], gap="small")
        with col1:
            st.markdown(f"""
            <div class="card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;">
                    <div>
                        <div style="font-weight:700;font-size:1rem;color:var(--text-white);">
                            {item.get("weave_style","—")} · {item.get("color","—")}
                        </div>
                        <div style="font-size:0.78rem;color:var(--text-muted);margin-top:3px;">
                            Order #{item.get("order_id","—")} · {item.get("reason","—")}
                        </div>
                        <div style="margin:8px 0;">
                            {tags}
                            <span class="tag" style="background:rgba(34,197,94,0.15);color:#22c55e;">wholesale</span>
                            <span class="tag" style="background:rgba(34,197,94,0.15);color:#22c55e;">ready to ship</span>
                            <span class="tag" style="background:rgba(239,68,68,0.15);color:#ef4444;">rejected custom</span>
                        </div>
                        <div style="font-size:0.82rem;color:var(--text-primary);">
                            Woven by <b>{item.get("weaver_name","—")}</b> ·
                            {item.get("weaver_cluster","—")}, {item.get("weaver_state","—")}
                        </div>
                    </div>
                    <div style="text-align:right;flex-shrink:0;">
                        <div style="font-size:0.78rem;color:var(--text-muted);text-decoration:line-through;">
                            Rs.{orig:,}
                        </div>
                        <div class="swatch-price">Rs.{resale:,}</div>
                        <div style="background:rgba(34,197,94,0.2);color:#22c55e;padding:2px 8px;
                            border-radius:999px;font-size:0.72rem;font-weight:700;
                            display:inline-block;margin-top:2px;">{discount}% off</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown('<div style="height:0.6rem;"></div>', unsafe_allow_html=True)
            if st.button("Buy Now", key=f"buy_{item.get('order_id','')}_{idx}", use_container_width=True):
                st.success(f"{item.get('order_id','')} added to cart! Delivery: 3-5 days.")

        st.markdown('<div style="height:0.2rem;"></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    _render_header()

    if "app_loaded" not in st.session_state:
        st.markdown(
            '<div style="background:rgba(218,65,103,0.1);border:1px solid rgba(218,65,103,0.3);'
            'border-radius:8px;padding:0.5rem 1rem;font-size:0.82rem;color:var(--accent);margin-bottom:0.8rem;">'
            'First load — agent is warming up. This takes about 15 seconds.</div>',
            unsafe_allow_html=True,
        )
        st.session_state["app_loaded"] = True

    tab = st.radio(
        "View",
        ["Buyer — Describe Your Saree", "Weaver — Manage Orders", "One of a Kind — Resale"],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    if "Buyer" in tab:
        _buyer_page()
    elif "Weaver" in tab:
        _weaver_page()
    else:
        _ooak_page()


if __name__ == "__main__":
    main()
