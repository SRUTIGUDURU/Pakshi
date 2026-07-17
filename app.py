"""
Pakshi - Full Streamlit App (Tier-2/3 Buyer & Artisan Optimized)
================================================================
Buyer  : Bilingual voice/text input -> agent matches swatches -> trust-first confirmation
Weaver : Hands-free bidirectional audio commands (Accept/Reject/Show Buyer) + Min Base Filter
OOAK   : Zero-waste wholesale listing for rejected custom pieces
Onboard: Voice & GPS-assisted weaver registration with Hindi/English auto‑fill.

Run:
    pip install streamlit chromadb scikit-learn edge-tts SpeechRecognition requests
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
import requests  # for reverse geocoding

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
# Brand & Tier-2/3 Touch-Friendly CSS (truncated for brevity – keep your existing CSS)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ... your full CSS from earlier ... */
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

def _autoplay_audio(audio_bytes: bytes, fmt: str = "mp3") -> None:
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(
        f'<audio autoplay style="display:none">'
        f'<source src="data:audio/{fmt};base64,{b64}" type="audio/{fmt}">'
        f'</audio>',
        unsafe_allow_html=True,
    )

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

        # Try Hindi first
        try:
            text = recognizer.recognize_google(audio, language="hi-IN")
            if text and len(text.strip()) > 1: return text.strip(), None
        except sr.UnknownValueError: pass
        except sr.RequestError as e: return None, f"Speech recognition service unavailable: {e}"

        # Then English
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
# Natural Language Voice Command Parsers (buyer & weaver)
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
    t = text.lower()
    action = None
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

    target_list = accepted if action == "show_buyer" else pending
    if not target_list:
        return {"action": "error", "message": f"No {'in-production' if action == 'show_buyer' else 'pending'} orders available."}

    target_idx = None
    m = re.search(r'\b(\d{4})\b', t)
    if m:
        oid = m.group(1)
        for i, o in enumerate(target_list):
            if oid in o.get("order_id", ""):
                target_idx = i
                break

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
# Parser for weaver registration voice input (Hindi/English)
# ---------------------------------------------------------------------------
def _parse_registration_text(text: str) -> dict:
    """
    Extract name, cluster, specialty, phone from a transcribed voice message.
    Works for Hindi and English patterns.
    """
    result = {"name": "", "cluster": "", "specialty": "", "phone": ""}
    t = text.lower().strip()

    # Patterns: "mera naam X hai", "my name is X", "name X", etc.
    name_match = re.search(r'(?:mera naam|my name is|name is|naam)\s*(.+?)(?:\s+hai|\s*$|\.)', t, re.IGNORECASE)
    if name_match:
        result["name"] = name_match.group(1).strip().title()

    # Cluster: "cluster X hai", "cluster X", "X cluster", "X mein", "from X"
    cluster_match = re.search(r'(?:cluster|clusters?|group|area|from|से|में)\s*(.+?)(?:\s+(?:hai|is|mein|क्लस्टर)|$|\.)', t, re.IGNORECASE)
    if cluster_match:
        result["cluster"] = cluster_match.group(1).strip().title()

    # Specialty: "specialty X", "weave X", "X weave", "X banata hoon", "X ki weaving"
    specialty_match = re.search(r'(?:specialty|weave|weaving|बुनाई|काम|banata|karate)\s*(.+?)(?:\s+(?:hai|is|करता)|$|\.)', t, re.IGNORECASE)
    if specialty_match:
        result["specialty"] = specialty_match.group(1).strip().title()

    # Phone: 10-digit number
    phone_match = re.search(r'\b(\d{10})\b', t)
    if phone_match:
        result["phone"] = phone_match.group(1)

    # Fallback: if no name extracted but we have text, use first few words as name
    if not result["name"] and len(t.split()) >= 2:
        result["name"] = " ".join(t.split()[:2]).title()

    return result

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
    if "reg_parsed" not in st.session_state: st.session_state["reg_parsed"] = {}

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
# WEAVER PAGE (Voice Router + Min Base Price + Onboarding with Voice & GPS)
# ---------------------------------------------------------------------------
def _weaver_page() -> None:
    _init_weaver_state()
    all_weavers = _get_all_weavers()
    st.markdown('<div class="section-label">🧑‍🎨 Artisan Portal (बुनकर पोर्टल)</div>', unsafe_allow_html=True)

    # ---- ONBOARDING FORM with Voice & GPS ----
    with st.expander("🆕 Register as a New Weaver (हमसे जुड़ें)", expanded=False):
        # 1. GPS location button
        col_gps, _ = st.columns([1, 4])
        with col_gps:
            if st.button("📍 Get Current Location", help="Uses browser GPS to get your coordinates"):
                gps_js = """
                <script>
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        (pos) => {
                            const lat = pos.coords.latitude;
                            const lon = pos.coords.longitude;
                            window.location.href = window.location.pathname + '?lat=' + lat + '&lon=' + lon;
                        },
                        (err) => {
                            alert('GPS error: ' + err.message);
                        }
                    );
                } else {
                    alert('Geolocation not supported by this browser.');
                }
                </script>
                """
                st.components.v1.html(gps_js, height=0, width=0)

        # Read GPS from query params and store in session state
        lat = st.query_params.get("lat")
        lon = st.query_params.get("lon")
        if lat and lon:
            st.session_state["gps_coords"] = f"{lat}, {lon}"
            try:
                resp = requests.get(
                    f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=10",
                    headers={"User-Agent": "Pakshi-Hackathon"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "display_name" in data:
                        st.session_state["gps_place"] = data["display_name"].split(",")[0].strip()
            except Exception:
                pass
            st.query_params.clear()
            st.rerun()

        # 2. Voice input for registration (Hindi/English)
        st.markdown("**🎤 Speak Your Registration (बोलकर भरें)**")
        st.caption("Say your details in one go: e.g., 'My name is Ramesh, I weave Banarasi silk in Varanasi, phone 9876543210' or Hindi: 'Mera naam Ramesh hai, main Banarasi silk ki weaving karta hoon, phone 9876543210'")
        reg_audio = st.audio_input("Record registration details", key="reg_audio")
        if reg_audio is not None:
            with st.spinner("🎧 Transcribing..."):
                text, err = _transcribe_audio(reg_audio)
            if err:
                st.warning(err)
            else:
                st.info(f"🗣️ Heard: {text}")
                # Parse the text to extract fields
                parsed = _parse_registration_text(text)
                # Store parsed data in session state for auto-fill
                for key, val in parsed.items():
                    if val:
                        st.session_state[f"reg_{key}"] = val
                st.success("✅ Fields extracted! Please review and correct below.")
                st.rerun()

        # 3. Registration form – auto-filled from voice or GPS
        with st.form("weaver_onboarding"):
            # Pre-fill from session state or GPS
            default_name = st.session_state.get("reg_name", "")
            default_cluster = st.session_state.get("gps_place", "") or st.session_state.get("reg_cluster", "")
            default_specialty = st.session_state.get("reg_specialty", "")
            default_phone = st.session_state.get("reg_phone", "")
            default_gps = st.session_state.get("gps_coords", "")

            name = st.text_input("Full Name (पूरा नाम)", value=default_name, placeholder="e.g., Ramesh Kumar")
            cluster = st.text_input("Weaving Cluster (बुनकर समूह)", value=default_cluster, placeholder="e.g., Pochampally, Banaras")
            specialty = st.text_input("Speciality Weave (विशेषता)", value=default_specialty, placeholder="e.g., Ikat, Banarasi Brocade")
            phone = st.text_input("Phone (मोबाइल)", value=default_phone, placeholder="e.g., 9876543210")
            gps_display = st.text_input("GPS Coordinates (auto-detected)", value=default_gps, disabled=True)

            submitted = st.form_submit_button("✅ Register Weaver")
            if submitted:
                if name.strip() and cluster.strip() and specialty.strip():
                    new_id = f"CW{random.randint(100,999)}"
                    new_profile = {
                        "id": new_id,
                        "name": name.strip(),
                        "cluster": cluster.strip(),
                        "state": "India",
                        "fabric_specialty": [specialty.strip()],
                        "weave_style": specialty.strip(),
                        "price_range_inr": {"min": 1000, "max": 5000},
                        "rating": 4.0,
                        "orders_completed": 0,
                        "active": True,
                        "onboarded": True,
                        "gps": gps_display if gps_display else "",
                        "phone": phone.strip(),
                    }
                    st.session_state.setdefault("custom_weavers", []).append(new_profile)
                    st.session_state["weaver_id"] = new_id
                    # Clear temporary session state
                    for k in ["reg_name", "reg_cluster", "reg_specialty", "reg_phone", "gps_coords", "gps_place"]:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.success(f"✅ Registered successfully! Weaver ID: {new_id}")
                    st.balloons()
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Please fill all required fields (Name, Cluster, Specialty).")

    # ---- Existing weaver dashboard (dropdown, orders, voice commands) ----
    col_sel, col_stat = st.columns([2, 3])
    with col_sel:
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

    # ---- Voice Router for Weavers ----
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
                idx = next((i for i, o in enumerate(orders) if o["order_id"] == oid), None)
                if idx is not None:
                    if act == "accept":
                        orders[idx]["status"] = "accepted"
                        for bo in st.session_state.get("buyer_orders", []):
                            if bo["order_id"] == oid:
                                bo["status"] = "In Production"
                        st.session_state["weaver_orders"] = orders
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
                st.error(msg)
        st.rerun()

    # ---- Display Order Queues ----
    if st.session_state.get("audio_work_mode") and (pending or accepted):
        if st.button("🔊 Read My Orders Aloud", use_container_width=False):
            lines = []
            if pending:
                lines.append(f"Aapke paas {len(pending)} naye order hain.")
                for o in pending[:3]:
                    lines.append(
                        f"Order {o.get('order_id','')[-4:]}: "
                        f"{o.get('weave_style','fabric')}, {o.get('color','')}, "
                        f"keemat {o.get('price',0)} rupaye, deliver by {o.get('delivery_by','')}."
                    )
            if accepted:
                lines.append(f"{len(accepted)} order loom par chal rahe hain.")
                for o in accepted[:2]:
                    lines.append(
                        f"Order {o.get('order_id','')[-4:]}: "
                        f"{o.get('weave_style','fabric')}, deliver by {o.get('delivery_by','')}."
                    )
            full_text = " ".join(lines)
            if ab := _tts_bytes(full_text, lang="hi"):
                _autoplay_audio(ab)
            else:
                st.warning("Audio not available.")

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

            if st.button(f"📸 Send Fabric Photo for Approval (#{order['order_id']})", key=f"show_{order['order_id']}"):
                orders[idx]["status"] = "awaiting_approval"
                orders[idx]["photo"] = "loom_manual.jpg"
                st.session_state["weaver_orders"] = orders
                for bo in st.session_state.get("buyer_orders", []):
                    if bo["order_id"] == order["order_id"]:
                        bo["status"] = "Awaiting Approval"
                        bo["photo_path"] = "loom_manual.jpg"
                if ab := _tts_bytes("Tasveer bhej di gayi hai.", lang="hi"): _autoplay_audio(ab)
                st.success("Photo sent! Awaiting buyer approval.")
                st.rerun()

    awaiting = [o for o in orders if o.get("status") == "awaiting_approval"]
    if awaiting:
        st.markdown('<div class="section-label" style="margin-top:1rem;">⏳ Awaiting Buyer Approval</div>', unsafe_allow_html=True)
        for order in awaiting:
            st.info(f"Order #{order['order_id']} is pending approval from the buyer on Meesho.")

    st.markdown('<div style="height:1.2rem;"></div>', unsafe_allow_html=True)
    if st.button("📡 Simulate New Incoming Broadcast", use_container_width=True):
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
def _ooak_page() -> None:
    st.markdown('<div class="section-label">♻️ One of a Kind — Wholesale Resale Outlet</div>', unsafe_allow_html=True)
    items = st.session_state.get("one_of_a_kind", [])
    if not items: return st.info("🌱 Zero Waste — No Rejected Pieces Currently Available")

    for idx, item in enumerate(items):
        orig, resale = item.get("original_price", 0), item.get("resale_price", 0)
        st.markdown(f"""
        <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div><div style="font-weight:800;font-size:1.05rem;color:var(--text-white);">{item.get("weave_style","—")}</div>
                     <div style="font-size:0.80rem;color:var(--text-muted);">Original Order #{item.get("order_id","—")}</div></div>
                <div style="text-align:right;"><div style="font-size:0.80rem;color:var(--text-muted);text-decoration:line-through;">₹{orig:,}</div>
                     <div class="swatch-price">₹{resale:,}</div></div>
            </div>
        </div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    _render_header()
    tab = st.radio("Nav", ["🛍️ Buyer Portal", "🧑‍🎨 Weaver Dashboard", "♻️ Wholesale Resale"], horizontal=True, label_visibility="collapsed")
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    if "Buyer" in tab: _buyer_page()
    elif "Weaver" in tab: _weaver_page()
    else: _ooak_page()

if __name__ == "__main__":
    main()
