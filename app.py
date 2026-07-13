"""
Pakshi — Full Streamlit App
============================
Buyer side : describe your saree in natural language -> agent finds swatches -> confirm order
Weaver side : see incoming orders -> accept/decline -> upload progress photo

Run with:
 pip install streamlit chromadb scikit-learn
 streamlit run app.py

All backend files must be in the same directory:
 intent_parser.py, agent.py, retrieval.py, setup_chromadb.py,
 fabric_ontology.json, fabric_swatches.json, weaver_profiles.json
"""

import json
import time
import random
from pathlib import Path
from dataclasses import asdict

import streamlit as st

# ---------------------------------------------------------------------------
# Page config — must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
 page_title="Pakshi",
 page_icon="",
 layout="wide",
 initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Brand CSS — purple / orange / dark, matching the deck
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* Root tokens */
:root {
 --purple-deep: #3d1a6e;
 --purple-mid: #5e2d9e;
 --purple-light: #7b3fc4;
 --orange: #f5a623;
 --orange-dark: #c47d0a;
 --white: #ffffff;
 --grey-soft: #e8e0f5;
 --grey-muted: #b0a8c8;
 --surface: #2a0f52;
 --card: #3a1870;
 --success: #22c55e;
 --danger: #ef4444;
}

/* Global */
html, body, [class*="css"] {
 font-family: 'Inter', sans-serif;
 background-color: var(--purple-deep);
 color: var(--white);
}
.main { background-color: var(--purple-deep); }
.block-container { padding: 1.5rem 2rem 3rem; max-width: 1100px; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* Wordmark */
.pakshi-wordmark {
 font-size: 2rem;
 font-weight: 800;
 color: var(--white);
 letter-spacing: -0.5px;
}
.pakshi-wordmark span { color: var(--orange); }

.tagline {
 font-size: 0.85rem;
 color: var(--grey-muted);
 margin-top: -4px;
 margin-bottom: 1.5rem;
}

/* Tab pills */
.tab-row {
 display: flex;
 gap: 0.5rem;
 margin-bottom: 1.5rem;
}
.tab-pill {
 padding: 0.45rem 1.2rem;
 border-radius: 999px;
 border: 1.5px solid var(--purple-light);
 background: transparent;
 color: var(--grey-muted);
 font-size: 0.85rem;
 font-weight: 600;
 cursor: pointer;
}
.tab-pill.active {
 background: var(--orange);
 border-color: var(--orange);
 color: var(--purple-deep);
}

/* Cards */
.card {
 background: var(--card);
 border: 1px solid rgba(255,255,255,0.08);
 border-radius: 12px;
 padding: 1.2rem 1.4rem;
 margin-bottom: 1rem;
}
.card-highlight {
 background: var(--card);
 border: 1.5px solid var(--orange);
 border-radius: 12px;
 padding: 1.2rem 1.4rem;
 margin-bottom: 1rem;
}

/* Swatch card */
.swatch-card {
 background: var(--surface);
 border: 1px solid rgba(255,255,255,0.1);
 border-radius: 10px;
 padding: 1rem;
 height: 100%;
}
.swatch-price {
 font-size: 1.4rem;
 font-weight: 800;
 color: var(--orange);
}
.swatch-label {
 font-size: 0.75rem;
 color: var(--grey-muted);
 text-transform: uppercase;
 letter-spacing: 0.05em;
}
.swatch-value {
 font-size: 0.9rem;
 font-weight: 500;
 color: var(--white);
}
.tag {
 display: inline-block;
 padding: 2px 8px;
 border-radius: 999px;
 background: rgba(245,166,35,0.15);
 color: var(--orange);
 font-size: 0.72rem;
 font-weight: 500;
 margin: 2px 2px 0 0;
}

/* Chat bubbles */
.bubble-agent {
 background: var(--card);
 border: 1px solid rgba(255,255,255,0.08);
 border-radius: 12px 12px 12px 2px;
 padding: 0.75rem 1rem;
 margin: 0.4rem 0;
 max-width: 82%;
 font-size: 0.88rem;
 line-height: 1.55;
 white-space: pre-wrap;
}
.bubble-user {
 background: var(--purple-light);
 border-radius: 12px 12px 2px 12px;
 padding: 0.75rem 1rem;
 margin: 0.4rem 0 0.4rem auto;
 max-width: 70%;
 font-size: 0.88rem;
 line-height: 1.55;
 text-align: right;
}

/* State badge */
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
.state-active { background: rgba(34,197,94,0.2); color: #22c55e; }
.state-pending { background: rgba(245,166,35,0.2); color: var(--orange); }
.state-done { background: rgba(94,45,158,0.4); color: var(--grey-soft); }

/* Section label */
.section-label {
 font-size: 0.72rem;
 font-weight: 700;
 text-transform: uppercase;
 letter-spacing: 0.12em;
 color: var(--orange);
 margin-bottom: 0.4rem;
}

/* Order confirmed banner */
.confirmed-banner {
 background: linear-gradient(135deg, #22c55e22, #22c55e0a);
 border: 1.5px solid #22c55e;
 border-radius: 12px;
 padding: 1.4rem;
 text-align: center;
 margin-top: 1rem;
}
.confirmed-banner h2 { color: #22c55e; margin: 0; font-size: 1.5rem; }

/* Weaver order card */
.order-card {
 background: var(--surface);
 border: 1px solid rgba(255,255,255,0.1);
 border-radius: 10px;
 padding: 1rem 1.2rem;
 margin-bottom: 0.8rem;
}
.order-card.accepted { border-color: #22c55e44; }
.order-card.declined { border-color: #ef444444; opacity: 0.6; }

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
 background-color: var(--surface) !important;
 color: var(--white) !important;
 border: 1.5px solid var(--purple-light) !important;
 border-radius: 8px !important;
 font-family: 'Inter', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
 border-color: var(--orange) !important;
 box-shadow: 0 0 0 2px rgba(245,166,35,0.25) !important;
}

/* Buttons */
.stButton > button {
 background: var(--orange) !important;
 color: var(--purple-deep) !important;
 font-weight: 700 !important;
 border: none !important;
 border-radius: 8px !important;
 padding: 0.5rem 1.4rem !important;
 font-family: 'Inter', sans-serif !important;
 transition: opacity 0.15s;
}
.stButton > button:hover { opacity: 0.88 !important; }

.stButton > button[kind="secondary"] {
 background: transparent !important;
 color: var(--grey-muted) !important;
 border: 1.5px solid var(--purple-light) !important;
}

/* Divider */
.pakshi-divider {
 height: 1px;
 background: rgba(255,255,255,0.08);
 margin: 1.2rem 0;
}

/* Agent reasoning box */
.reasoning-box {
 background: rgba(245,166,35,0.08);
 border-left: 3px solid var(--orange);
 border-radius: 0 8px 8px 0;
 padding: 0.75rem 1rem;
 font-size: 0.82rem;
 color: var(--grey-soft);
 font-style: italic;
 line-height: 1.6;
 margin: 0.6rem 0;
}

/* Progress step */
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
.step-dot.done { background: #22c55e; }
.step-dot.active { background: var(--orange); }
.step-dot.pending { background: var(--purple-light); opacity: 0.4; }

/* Radio overrides */
.stRadio > div { gap: 0.4rem; }
.stRadio label { font-size: 0.88rem !important; }

/* selectbox */
.stSelectbox > div > div {
 background-color: var(--surface) !important;
 color: var(--white) !important;
 border: 1.5px solid var(--purple-light) !important;
 border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Lazy import of backend (won't crash if user hasn't set up ChromaDB yet)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _load_agent_class():
 try:
 from agent import PakshiAgent
 return PakshiAgent, None
 except Exception as e:
 return None, str(e)

@st.cache_data(show_spinner=False)
def _load_weaver_profiles():
 try:
 p = Path(__file__).parent / "weaver_profiles.json"
 with open(p) as f:
 return json.load(f)["weaver_profiles"]
 except Exception:
 return []

# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------
def _init_buyer_state():
 defaults = {
 "agent": None,
 "history": [], # list of (role, text)
 "current_state": "greeting",
 "swatches": [],
 "selected_swatch":None,
 "order": None,
 "agent_data": {},
 "awaiting": None, # "swatch_select" | "fallback_yn" | "confirm" | None
 "reasoning_log": [],
 "one_of_a_kind": [], # rejected custom pieces -> resale
 }
 for k, v in defaults.items():
 if k not in st.session_state:
 st.session_state[k] = v

def _init_weaver_state():
 if "weaver_orders" not in st.session_state:
 # Simulate a few pending orders for demo
 st.session_state["weaver_orders"] = _make_demo_orders()
 if "weaver_id" not in st.session_state:
 st.session_state["weaver_id"] = "W001"

def _make_demo_orders():
 """Generate realistic demo orders for the weaver dashboard."""
 return [
 {
 "order_id": "PKS-2847",
 "fabric": "Cotton-Silk",
 "weave_style": "Pochampally Ikat",
 "color": "Teal with gold border",
 "occasion": "Summer Wedding",
 "buyer_feel": "flowy, breathable yet elegant",
 "price": 1800,
 "delivery_by": "July 26, 2026",
 "status": "pending",
 "photo": None,
 "buyer_note": "Light saree, summer wedding, ₹1500 — agent proposed Cotton-Silk at ₹1800",
 },
 {
 "order_id": "PKS-2831",
 "fabric": "Cotton",
 "weave_style": "Pochampally Ikat",
 "color": "Navy blue",
 "occasion": "Office / Daily Wear",
 "buyer_feel": "breathable, cool, non-itchy",
 "price": 750,
 "delivery_by": "July 20, 2026",
 "status": "accepted",
 "photo": None,
 "buyer_note": "Office wear, breathable cotton under ₹800",
 },
 {
 "order_id": "PKS-2819",
 "fabric": "Silk",
 "weave_style": "Pochampally Ikat",
 "color": "Deep red with zari",
 "occasion": "Wedding Reception",
 "buyer_feel": "royal, heavy, grand",
 "price": 4200,
 "delivery_by": "August 2, 2026",
 "status": "pending",
 "photo": None,
 "buyer_note": "Sister's wedding reception, deep red silk, grand",
 },
 ]

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
def _render_header():
 c1, c2 = st.columns([1, 3])
 with c1:
 st.markdown(
 '<div class="pakshi-wordmark">Pakshi</div>'
 '<div class="tagline">Turning buyer intent into artisan opportunity</div>',
 unsafe_allow_html=True
 )

# ---------------------------------------------------------------------------
# BUYER SIDE
# ---------------------------------------------------------------------------

STATE_STEPS = [
 ("greeting", "Start"),
 ("collecting", "Intent"),
 ("retrieved", "Swatches"),
 ("fallback_pending", "Fallback"),
 ("swatch_selected", "Locked"),
 ("broadcasting", "Broadcast"),
 ("weaver_selected", "Matched"),
 ("confirmed", "Confirmed"),
]

def _step_indicator(current: str):
 active_idx = next((i for i,(k,_) in enumerate(STATE_STEPS) if k == current), 0)
 html = '<div style="display:flex;gap:1.2rem;align-items:center;margin-bottom:1rem;flex-wrap:wrap;">'
 for i, (key, label) in enumerate(STATE_STEPS):
 if key in ("fallback_pending", "broadcasting", "weaver_selected"):
 continue # internal states, skip visual
 cls = "done" if i < active_idx else ("active" if i == active_idx else "pending")
 html += (
 f'<div class="step-row">'
 f' <div class="step-dot {cls}"></div>'
 f' <span style="font-size:0.78rem;color:{"#22c55e" if cls=="done" else ("var(--orange)" if cls=="active" else "var(--grey-muted)")};">'
 f' {label}</span>'
 f'</div>'
 )
 html += '</div>'
 st.markdown(html, unsafe_allow_html=True)

def _render_swatch_card(i: int, swatch: dict):
 fabric_icon = {"cotton": "", "silk": "", "cotton_silk": ""}.get(
 swatch.get("fabric_type", ""), ""
 )
 tags_html = "".join(
 f'<span class="tag">{t}</span>'
 for t in (swatch.get("sensory_tags", [])[:3])
 )
 st.markdown(f"""
 <div class="swatch-card">
 <div style="font-size:1.5rem;margin-bottom:4px">{fabric_icon}</div>
 <div style="font-weight:700;font-size:0.95rem;margin-bottom:2px">
 {swatch.get('weave_style','—')}
 </div>
 <div style="font-size:0.82rem;color:var(--grey-muted);margin-bottom:8px">
 {swatch.get('color','—')}
 </div>
 <div class="swatch-price">₹{swatch.get('price_inr','?')}</div>
 <div style="margin:8px 0">{tags_html}</div>
 <div class="pakshi-divider"></div>
 <div class="swatch-label">Weaver</div>
 <div class="swatch-value">{swatch.get('weaver_name','—')}</div>
 <div style="font-size:0.78rem;color:var(--grey-muted)">
 {swatch.get('weaver_cluster','')}, {swatch.get('weaver_state','')}
 </div>
 <div style="margin-top:4px;font-size:0.82rem">
 {swatch.get('weaver_rating','?')} &nbsp;·&nbsp;
 {swatch.get('delivery_days','?')} days
 </div>
 </div>
 """, unsafe_allow_html=True)

def _send_message(user_text: str):
 """Send a message through the agent and update session state."""
 PakshiAgent, err = _load_agent_class()
 if err:
 st.error(f"Backend not loaded: {err}")
 return

 if st.session_state["agent"] is None:
 st.session_state["agent"] = PakshiAgent()

 agent = st.session_state["agent"]
 st.session_state["history"].append(("user", user_text))

 response = agent.chat(user_text)
 msg = response.get("message", "")
 state = response.get("state", "greeting")
 data = response.get("data", {})

 st.session_state["current_state"] = state
 st.session_state["history"].append(("agent", msg))
 st.session_state["agent_data"] = data

 # Extract swatches if present
 if data.get("swatches"):
 st.session_state["swatches"] = data["swatches"]

 # Extract confirmed order
 if data.get("order"):
 st.session_state["order"] = data["order"]

 # Log reasoning for "Why It's Agentic" panel
 if state in ("fallback_pending", "broadcasting", "weaver_selected", "confirmed"):
 st.session_state["reasoning_log"].append(f"[{state.upper()}] {msg[:120]}…")

def _buyer_page():
 _init_buyer_state()

 st.markdown('<div class="section-label">Buyer</div>', unsafe_allow_html=True)

 with st.expander("How to use this app (Buyer)"):
     st.markdown("""
**Step 1 — Speak or type your request.**
Click the microphone and describe what you want in your own words and language,
for example: *"Light saree for summer wedding, Rs.1500, mint green."*
You can also type the same in the text box below.

**Step 2 — Review swatches.**
The agent will show up to 3 matching handloom swatches. Each card shows
the fabric, weave style, colour, price, weaver name, and delivery estimate.

**Step 3 — Select a swatch.**
Type 1, 2, or 3 (or click the Select button) to lock your choice.
This sets the expectation before production begins.

**Step 4 — Confirm the order.**
Click Confirm Order. The agent autonomously selects the best available
weaver based on proximity and delivery history. Your order is placed on Meesho.

**Step 5 — Reject if needed.**
If the finished piece does not match your expectation, click
Reject Piece. It moves to the One of a Kind resale tab at a wholesale price.
No waste, no loss.
     """)

 _step_indicator(st.session_state["current_state"])

 # Layout: chat left | panel right 
 col_chat, col_panel = st.columns([3, 2], gap="large")

 # RIGHT PANEL 
 with col_panel:
 # Swatches
 swatches = st.session_state["swatches"]
 if swatches:
 st.markdown('<div class="section-label">Matching Swatches</div>', unsafe_allow_html=True)
 for i, sw in enumerate(swatches[:3]):
 _render_swatch_card(i + 1, sw)
 if st.session_state["current_state"] == "retrieved":
 if st.button(f"Select Swatch {i+1}", key=f"sel_{i}"):
 _send_message(str(i + 1))
 st.rerun()

 # Confirmed order summary
 order = st.session_state["order"]
 if order and st.session_state["current_state"] == "confirmed":
 sw = order.get("selected_swatch") or {}
 wv = order.get("selected_weaver") or {}
 st.markdown(f"""
 <div class="confirmed-banner">
 <h2> Order Confirmed</h2>
 <div style="font-size:0.82rem;color:#86efac;margin-top:4px">
 #{order.get('order_id','—')}
 </div>
 <div style="margin-top:12px;text-align:left">
 <div class="swatch-label">Fabric</div>
 <div class="swatch-value">
 {sw.get('weave_style','—')} · {sw.get('color','—')}
 </div>
 <div class="swatch-price" style="margin:6px 0">
 ₹{sw.get('price_inr','?')}
 </div>
 <div class="pakshi-divider"></div>
 <div class="swatch-label">Weaver (agent-selected)</div>
 <div class="swatch-value">{wv.get('weaver_name','—')}</div>
 <div style="font-size:0.78rem;color:var(--grey-muted)">
 {wv.get('weaver_cluster','')}, {wv.get('weaver_state','')} ·
 {wv.get('weaver_rating','?')} ·
 {wv.get('delivery_days','?')} days
 </div>
 </div>
 </div>
 """, unsafe_allow_html=True)

 # Reject / One of a Kind flow 
 st.markdown('<div class="pakshi-divider"></div>', unsafe_allow_html=True)
 st.markdown('<div class="section-label">Not satisfied? Reject this piece.</div>',
 unsafe_allow_html=True)
 st.caption(
 "If the final product doesn't meet your expectation, move it to our "
 "'One of a Kind' resale category. The weaver recovers partial value, "
 "you owe nothing, and a unique piece finds a new buyer."
 )
 if st.button("Reject Piece — Move to One of a Kind", use_container_width=True):
 current_order = st.session_state["order"]
 if current_order:
 swatch = current_order.get("selected_swatch") or {}
 weaver = current_order.get("selected_weaver") or {}
 original_price = swatch.get("price_inr", 0)
 resale_price = int(original_price * 0.6)
 rejected_item = {
 "order_id": current_order.get("order_id", "PKS-XXXX"),
 "weave_style": swatch.get("weave_style", "Unknown"),
 "color": swatch.get("color", "Unknown"),
 "original_price": original_price,
 "resale_price": resale_price,
 "weaver_name": weaver.get("weaver_name", "Unknown"),
 "weaver_cluster": weaver.get("weaver_cluster", "Unknown"),
 "weaver_state": weaver.get("weaver_state", "Unknown"),
 "sensory_tags": swatch.get("sensory_tags", []),
 "reason": "Weaving imperfection / colour mismatch",
 }
 if "one_of_a_kind" not in st.session_state:
 st.session_state["one_of_a_kind"] = []
 st.session_state["one_of_a_kind"].append(rejected_item)
 # Reset buyer session for a new search
 st.session_state["current_state"] = "greeting"
 st.session_state["order"] = None
 st.session_state["swatches"] = []
 st.session_state["history"] = []
 st.session_state["agent"] = None
 st.session_state["reasoning_log"] = []
 st.success(
 f"Piece moved to One of a Kind at ₹{resale_price:,}. "
 "Starting a fresh search for you."
 )
 st.rerun()

 # Agent reasoning log
 if st.session_state["reasoning_log"]:
 st.markdown('<div class="section-label" style="margin-top:1rem">Agent Reasoning</div>',
 unsafe_allow_html=True)
 for line in st.session_state["reasoning_log"][-3:]:
 st.markdown(f'<div class="reasoning-box">{line}</div>',
 unsafe_allow_html=True)

 # LEFT PANEL: Chat 
 with col_chat:
 # Render history
 for role, text in st.session_state["history"]:
 if role == "agent":
 st.markdown(
 f'<div class="bubble-agent">{text}</div>',
 unsafe_allow_html=True
 )
 else:
 st.markdown(
 f'<div class="bubble-user">{text}</div>',
 unsafe_allow_html=True
 )

 st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

 cur = st.session_state["current_state"]

 # Fallback YES/NO buttons 
 if cur == "fallback_pending":
 st.markdown('<div class="section-label">Agent is proposing an alternative</div>',
 unsafe_allow_html=True)
 c1, c2 = st.columns(2)
 with c1:
 if st.button("Yes, show alternatives", use_container_width=True):
 _send_message("yes")
 st.rerun()
 with c2:
 if st.button("No, wait for my budget", use_container_width=True):
 _send_message("no")
 st.rerun()

 # Confirm button when swatch is locked 
 elif cur == "swatch_selected":
 st.markdown('<div class="section-label">Swatch locked — ready to place order?</div>',
 unsafe_allow_html=True)
 c1, c2 = st.columns(2)
 with c1:
 if st.button("Confirm Order", use_container_width=True):
 _send_message("confirm")
 st.rerun()
 with c2:
 if st.button("Change Selection", use_container_width=True):
 _send_message("back")
 st.rerun()

 # Reset after confirmed / failed 
 elif cur in ("confirmed", "failed"):
 if st.button("Start New Search"):
 for k in list(st.session_state.keys()):
 del st.session_state[k]
 st.rerun()

 # Normal text input 
 else:
 # Greeting auto-send
 if cur == "greeting" and not st.session_state["history"]:
 _send_message("hi")
 st.rerun()

 # Voice input (Whisper STT) 
 if cur not in ("confirmed", "failed"):
 st.markdown(
 '<div class="section-label">Speak your request</div>',
 unsafe_allow_html=True
 )
 # --- Mic Permission Handling ---
 try:
 audio_file = st.audio_input(
 "\U0001f3a4 Record your fabric request",
 label_visibility="collapsed",
 key="audio_input"
 )
 except Exception as e:
 if "Permission denied" in str(e) or "not allowed" in str(e):
 st.warning("\u26a0\ufe0f Microphone access was denied. Please allow microphone access in your browser settings, or type your request below.")
 audio_file = None
 else:
 st.error(f"Error accessing microphone: {e}")
 audio_file = None
 if audio_file:
 with st.spinner("Transcribing..."):
 try:
 import whisper
 import tempfile

 @st.cache_resource
 def _load_whisper():
 return whisper.load_model("tiny")

 model = _load_whisper()
 with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
 tmp.write(audio_file.getbuffer())
 tmp_path = tmp.name

 result = model.transcribe(tmp_path)
 transcribed = result["text"].strip()

 if transcribed:
 st.success(f"Heard: {transcribed}")
 _send_message(transcribed)
 st.rerun()
 else:
 st.warning("Could not hear anything. Please try again or type below.")

 except Exception as e:
 st.error(f"Transcription error: {e}. Please type your request below.")

 st.markdown(
 '<div class="section-label" style="margin-top:0.8rem">Or type</div>',
 unsafe_allow_html=True
 )

 placeholder_map = {
 "collecting": "e.g. Light saree for summer wedding, Rs.1500, mint green...",
 "retrieved": "Type 1, 2, or 3 to select a swatch...",
 }
 placeholder = placeholder_map.get(cur, "Type your message...")

 with st.form("chat_form", clear_on_submit=True):
 user_input = st.text_input(
 "Your message",
 placeholder=placeholder,
 label_visibility="collapsed",
 )
 submitted = st.form_submit_button("Send")

 if submitted and user_input.strip():
 _send_message(user_input.strip())
 st.rerun()

 # Quick example chips — only show before first real message
 if cur in ("greeting", "collecting") and len(st.session_state["history"]) <= 1:
 st.markdown('<div style="margin-top:0.6rem"></div>', unsafe_allow_html=True)
 st.markdown('<div class="section-label">Try saying…</div>', unsafe_allow_html=True)
 examples = [
 "Light saree for summer wedding, ₹1500",
 "Shaadi ke liye flowy cotton, around ₹2000",
 "Something royal for reception, deep red silk, ₹8000",
 "Breathable office saree, ₹700, navy blue",
 ]
 cols = st.columns(2)
 for i, ex in enumerate(examples):
 with cols[i % 2]:
 if st.button(ex, key=f"ex_{i}"):
 _send_message(ex)
 st.rerun()

# ---------------------------------------------------------------------------
# WEAVER SIDE
# ---------------------------------------------------------------------------

def _weaver_page():
 _init_weaver_state()

 weavers = _load_weaver_profiles()
 weaver_names = {w["id"]: w["name"] for w in weavers}

 st.markdown('<div class="section-label">Weaver Dashboard</div>', unsafe_allow_html=True)

 with st.expander("How to use this app (Weaver)"):
     st.markdown("""
**Step 1 — Select your weaver profile.**
Use the dropdown at the top to log in as yourself. Your cluster, speciality,
rating, and completed orders will appear alongside.

**Step 2 — Review pending orders.**
New orders broadcast by the Pakshi agent appear under Pending. Each card shows
the fabric, weave style, colour, occasion, buyer's description, price, and
delivery deadline.

**Step 3 — Accept or decline.**
Click Accept to take the order. The buyer is notified and production begins.
Click Decline if you cannot fulfil it. The agent will find another weaver.

**Step 4 — Upload a progress photo.**
Once you start weaving, upload a mid-production photo. It is shared with
the buyer for preview and builds trust before delivery.

**Step 5 — Simulate a new broadcast.**
Click the Simulate New Order Broadcast button to see how incoming orders
arrive in real time during the demo.
     """)

 # Weaver selector (simulates different weavers logging in)
 col_sel, col_stat = st.columns([2, 3])
 with col_sel:
 weaver_options = [f"{w['id']} — {w['name']} ({w['cluster']})" for w in weavers[:10]]
 selected = st.selectbox("Logged in as", weaver_options, label_visibility="collapsed")
 wid = selected.split(" — ")[0]
 st.session_state["weaver_id"] = wid

 profile = next((w for w in weavers if w["id"] == wid), {})

 with col_stat:
 if profile:
 st.markdown(f"""
 <div style="display:flex;gap:1.5rem;align-items:center;padding:0.5rem 0">
 <div>
 <div class="swatch-label">Cluster</div>
 <div class="swatch-value" style="font-size:0.85rem">{profile.get('cluster','')}</div>
 </div>
 <div>
 <div class="swatch-label">Speciality</div>
 <div class="swatch-value" style="font-size:0.85rem">
 {', '.join(profile.get('fabric_specialty',[]))}
 </div>
 </div>
 <div>
 <div class="swatch-label">Rating</div>
 <div class="swatch-value" style="font-size:0.85rem">{profile.get('rating','?')}</div>
 </div>
 <div>
 <div class="swatch-label">Orders done</div>
 <div class="swatch-value" style="font-size:0.85rem">{profile.get('orders_completed','?')}</div>
 </div>
 </div>
 """, unsafe_allow_html=True)

 st.markdown('<div class="pakshi-divider"></div>', unsafe_allow_html=True)

 orders = st.session_state["weaver_orders"]
 pending = [o for o in orders if o["status"] == "pending"]
 accepted = [o for o in orders if o["status"] == "accepted"]
 declined = [o for o in orders if o["status"] == "declined"]

 # Stats row
 c1, c2, c3 = st.columns(3)
 with c1:
 st.markdown(f"""
 <div class="card" style="text-align:center">
 <div style="font-size:1.8rem;font-weight:800;color:var(--orange)">{len(pending)}</div>
 <div class="swatch-label">Pending</div>
 </div>""", unsafe_allow_html=True)
 with c2:
 st.markdown(f"""
 <div class="card" style="text-align:center">
 <div style="font-size:1.8rem;font-weight:800;color:#22c55e">{len(accepted)}</div>
 <div class="swatch-label">Accepted</div>
 </div>""", unsafe_allow_html=True)
 with c3:
 total_value = sum(o["price"] for o in accepted)
 st.markdown(f"""
 <div class="card" style="text-align:center">
 <div style="font-size:1.8rem;font-weight:800;color:var(--orange)">₹{total_value:,}</div>
 <div class="swatch-label">Value in hand</div>
 </div>""", unsafe_allow_html=True)

 st.markdown('<div style="height:0.4rem"></div>', unsafe_allow_html=True)

 # Pending orders 
 if pending:
 st.markdown('<div class="section-label">New Orders — Awaiting Your Response</div>',
 unsafe_allow_html=True)
 for order in pending:
 idx = next(i for i, o in enumerate(orders) if o["order_id"] == order["order_id"])
 with st.container():
 st.markdown(f"""
 <div class="order-card">
 <div style="display:flex;justify-content:space-between;align-items:flex-start">
 <div>
 <div style="font-weight:700;font-size:0.95rem">
 {order['weave_style']} · {order['color']}
 </div>
 <div style="font-size:0.78rem;color:var(--grey-muted);margin-top:2px">Order #{order['order_id']} · {order['occasion']}
 </div>
 </div>
 <div class="swatch-price">₹{order['price']:,}</div>
 </div>
 <div style="margin-top:8px;font-size:0.82rem;color:var(--grey-soft)">
 <b>Buyer says:</b> "{order['buyer_note']}"
 </div>
 <div style="margin-top:6px">
 {"".join(f'<span class="tag">{t}</span>' for t in order['buyer_feel'].split(', ')[:4])}
 </div>
 <div style="margin-top:8px;font-size:0.78rem;color:var(--grey-muted)">Deliver by {order['delivery_by']}
 </div>
 </div>
 """, unsafe_allow_html=True)

 c1, c2, _ = st.columns([1, 1, 3])
 with c1:
 if st.button("Accept", key=f"acc_{order['order_id']}", use_container_width=True):
 st.session_state["weaver_orders"][idx]["status"] = "accepted"

 # --- Weaver TTS (Critical) ---
 try:
 from gtts import gTTS
 import tempfile, os, threading

 order_text = (
 f"New order: {order['weave_style']}, {order['color']}, "
 f"₹{order['price']}, due {order['delivery_by']}"
 )
 tts = gTTS(text=order_text, lang="hi", slow=False)
 with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
 tts.save(tmp.name)
 st.audio(tmp.name, format="audio/mp3")
 st.caption("Weaver, listen to the order details")

 threading.Timer(10.0, lambda: os.unlink(tmp.name) if os.path.exists(tmp.name) else None).start()
 except Exception:
 st.info("Audio playback not available. Order accepted.")

 st.success(f"Order {order['order_id']} accepted! Buyer will be notified.")
 time.sleep(0.5)
 st.rerun()
 with c2:
 if st.button("Decline", key=f"dec_{order['order_id']}",
 use_container_width=True):
 st.session_state["weaver_orders"][idx]["status"] = "declined"
 st.info("Order declined. Agent will find another weaver.")
 time.sleep(0.5)
 st.rerun()

 # Accepted orders 
 if accepted:
 st.markdown('<div class="section-label" style="margin-top:1rem">In Production</div>',
 unsafe_allow_html=True)
 for order in accepted:
 idx = next(i for i, o in enumerate(orders) if o["order_id"] == order["order_id"])
 st.markdown(f"""
 <div class="order-card accepted">
 <div style="display:flex;justify-content:space-between">
 <div>
 <div style="font-weight:700;font-size:0.9rem">
 {order['weave_style']} · {order['color']}
 </div>
 <div style="font-size:0.75rem;color:var(--grey-muted)">
 #{order['order_id']} · Due {order['delivery_by']}
 </div>
 </div>
 <div class="state-badge state-active">In Production</div>
 </div>
 </div>
 """, unsafe_allow_html=True)

 # Photo upload
 uploaded = st.file_uploader(
 f"Upload progress photo — {order['order_id']}",
 type=["jpg", "jpeg", "png"],
 key=f"photo_{order['order_id']}",
 label_visibility="collapsed",
 )
 if uploaded:
 st.image(uploaded, caption=f"Progress: {order['order_id']}", width=280)
 st.success("Photo sent to buyer for preview!")
 st.session_state["weaver_orders"][idx]["photo"] = uploaded.name

 st.markdown('<div style="height:0.4rem"></div>', unsafe_allow_html=True)

 # Declined 
 if declined:
 st.markdown('<div class="section-label" style="margin-top:1rem;color:var(--grey-muted)">Declined</div>',
 unsafe_allow_html=True)
 for order in declined:
 st.markdown(f"""
 <div class="order-card declined">
 <span style="font-size:0.85rem">{order['weave_style']} · #{order['order_id']}</span>
 <span style="float:right;font-size:0.75rem;color:var(--grey-muted)">Declined</span>
 </div>
 """, unsafe_allow_html=True)

 # Refresh simulation button
 st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
 if st.button("Simulate New Order Broadcast"):
 new_order = {
 "order_id": f"PKS-{random.randint(2900,2999)}",
 "fabric": random.choice(["Cotton-Silk", "Cotton", "Silk"]),
 "weave_style": profile.get("weave_style", "Handloom"),
 "color": random.choice(["Sage green", "Mustard yellow", "Ivory with zari", "Teal"]),
 "occasion": random.choice(["Wedding", "Festival", "Casual"]),
 "buyer_feel": random.choice(["light, flowy, elegant", "royal, heavy, grand", "breathable, cool"]),
 "price": random.choice([900, 1200, 1500, 2000, 2500]),
 "delivery_by": "July 25, 2026",
 "status": "pending",
 "photo": None,
 "buyer_note": "New broadcast from Pakshi agent",
 }
 st.session_state["weaver_orders"].insert(0, new_order)
 st.success("New order broadcast received!")
 st.rerun()

# ---------------------------------------------------------------------------
# ONE OF A KIND PAGE
# ---------------------------------------------------------------------------

def _one_of_a_kind_page():
 """Show rejected pieces available at wholesale prices."""
 st.markdown(
 '<div class="section-label">One of a Kind — Rejected Custom Pieces</div>',
 unsafe_allow_html=True
 )

 if "one_of_a_kind" not in st.session_state:
 st.session_state["one_of_a_kind"] = []

 items = st.session_state["one_of_a_kind"]

 if not items:
 st.markdown("""
 <div class="card" style="text-align:center;padding:2.5rem">
 <div style="font-size:2rem;margin-bottom:0.5rem"></div>
 <div style="font-weight:700;margin-bottom:0.4rem">No pieces here yet</div>
 <div style="font-size:0.85rem;color:var(--grey-muted)">When a buyer rejects a custom order, it appears here at wholesale price.<br>No waste. No loss written off entirely.
 </div>
 </div>
 """, unsafe_allow_html=True)
 return

 st.caption(
 f"{len(items)} unique handwoven piece{'s' if len(items)>1 else ''} available at "
 "wholesale prices — ready to ship, each one of a kind."
 )
 st.markdown('<div class="pakshi-divider"></div>', unsafe_allow_html=True)

 for item in items:
 original = item.get("original_price", 0)
 resale = item.get("resale_price", 0)
 discount = int((1 - resale / original) * 100) if original else 0
 tags_html = "".join(
 f'<span class="tag">{t}</span>'
 for t in item.get("sensory_tags", [])[:3]
 )

 col1, col2 = st.columns([4, 1], gap="small")
 with col1:
 st.markdown(f"""
 <div class="card">
 <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem">
 <div>
 <div style="font-weight:700;font-size:1rem">
 {item.get('weave_style','—')} &nbsp;·&nbsp; {item.get('color','—')}
 </div>
 <div style="font-size:0.78rem;color:var(--grey-muted);margin-top:3px">Order #{item.get('order_id','—')} · {item.get('reason','—')}
 </div>
 <div style="margin:8px 0">
 {tags_html}
 <span class="tag" style="background:rgba(34,197,94,0.15);color:#22c55e">wholesale</span>
 <span class="tag" style="background:rgba(34,197,94,0.15);color:#22c55e">ready to ship</span>
 <span class="tag" style="background:rgba(239,68,68,0.15);color:#ef4444">rejected custom</span>
 </div>
 <div style="font-size:0.82rem;color:var(--grey-soft)">Woven by <b>{item.get('weaver_name','—')}</b> ·
 {item.get('weaver_cluster','—')}, {item.get('weaver_state','—')}
 </div>
 </div>
 <div style="text-align:right;flex-shrink:0">
 <div style="font-size:0.78rem;color:var(--grey-muted);text-decoration:line-through">
 ₹{original:,}
 </div>
 <div class="swatch-price">₹{resale:,}</div>
 <div style="background:rgba(34,197,94,0.2);color:#22c55e;padding:2px 8px;
 border-radius:999px;font-size:0.72rem;font-weight:700;
 display:inline-block;margin-top:2px">
 {discount}% off
 </div>
 </div>
 </div>
 </div>
 """, unsafe_allow_html=True)

 with col2:
 st.markdown('<div style="height:0.6rem"></div>', unsafe_allow_html=True)
 if st.button(
 "Buy Now",
 key=f"buy_{item.get('order_id','')}_{items.index(item)}",
 use_container_width=True
 ):
 st.success(
 f" {item.get('order_id')} added to cart! "
 "Estimated delivery: 3–5 days."
 )

 st.markdown('<div style="height:0.2rem"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Main app — tab switcher
# ---------------------------------------------------------------------------
def main():
 _render_header()

 # Tab switcher using radio (styled as pills via CSS)
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
