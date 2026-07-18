"""
Pakshi - Full Streamlit App (Tier-2/3 Buyer & Artisan Optimized)
================================================================
Buyer  : Bilingual voice/text input -> agent matches swatches -> trust-first confirmation
Weaver : Hands-free bidirectional audio commands (Accept/Reject/Show Buyer) + Min Base Filter
OOAK   : Zero-waste wholesale listing for rejected custom pieces
Onboard: Voice & GPS-assisted weaver registration with auto-fill.

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
import requests

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Pakshi — Handloom Direct",
    page_icon="🪶",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# UI Language Strings
# ---------------------------------------------------------------------------
UI_STRINGS = {
    "en": {
        "app_title": "Pakshi — Handloom Direct",
        "tagline": "Direct from India's Master Weavers · Zero Middlemen Markup",
        "meesho_badge": "Meesho Verified Made-to-Order Handloom Vertical",
        "trust_banner": "✅ 100% Handloom Verified · 💵 Pay on Delivery Available · 🚚 Direct Factory Shipping",
        "nav_buyer": "Buyer Portal",
        "nav_weaver": "Weaver Dashboard",
        "nav_ooak": "One of a Kind",
        "nav_onboard": "Weaver Onboarding",
        "step_start": "Start",
        "step_intent": "Describe Intent",
        "step_swatch": "Select Swatch",
        "step_lock": "Lock Fabric",
        "step_confirm": "Order Placed",
        "btn_select": "Select Option",
        "btn_confirm": "Confirm Order & Place",
        "btn_back": "Back to Selection",
        "btn_new_search": "✨ Start New Saree Search",
        "btn_yes_alt": "✅ Yes, Show Alternatives",
        "btn_no_alt": "❌ No, Keep Original Specs",
        "btn_cancel_order": "❌ Cancel Order",
        "btn_approve": "✅ Approve and Ship",
        "btn_reject": "❌ Reject Piece",
        "btn_buy_now": "Buy Now",
        "section_swatches": "🎨 Recommended Artisanal Swatches",
        "section_orders": "📦 Your Active Orders",
        "agent_thinking": "⏳ Agent is finding matching artisans for you...",
        "order_status_production": "In Production",
        "order_status_approval": "Awaiting Approval",
        "order_status_completed": "Completed",
        "order_status_photo_sent": "Photo Sent — Awaiting Approval",
        "weaver_dashboard_title": "🧑‍🎨 Artisan Portal (बुनकर पोर्टल)",
        "weaver_min_base": "🛡️ Minimum Base Price Threshold",
        "weaver_audio_mode": "🔊 Hands-Free Loom Audio Mode",
        "weaver_voice_controls": "🎙️ Voice Loom Controls (हाथों के बिना काम करें)",
        "weaver_voice_caption": "Say 'Pehla order swikaar karo' (Accept first), 'Order 2847 mana karo' (Reject), or 'Buyer ko dikhao' (Send photo to buyer).",
        "weaver_read_orders": "Read My Orders Aloud",
        "weaver_pending": "📥 Pending Broadcasts",
        "weaver_production": "🧵 In Production (लूम पर)",
        "weaver_awaiting": "⏳ Awaiting Buyer Approval",
        "weaver_simulate": "📡 Simulate New Incoming Broadcast",
        "weaver_accept": "✅ Accept",
        "weaver_decline": "❌ Decline",
        "weaver_send_photo": "Send Photo for Buyer Approval",
        "onboard_title": "Weaver Onboarding — Join the Pakshi Network",
        "onboard_desc": "Powered by Meesho — Once you complete onboarding, your weaver profile goes live on the Pakshi network. Buyers describe what they want, the agent matches you, and orders come directly to your phone. No middlemen. Your craft. Your price.",
        "onboard_submitted": "✅ Profile Live!",
        "onboard_go_dashboard": "Go to Weaver Dashboard",
        "onboard_register_another": "Register Another Weaver",
        "onboard_basic": "Basic Details",
        "onboard_name": "Full Name (पूरा नाम)",
        "onboard_phone": "Mobile / WhatsApp Number",
        "onboard_cluster": "Village / Cluster (गांव / क्लस्टर)",
        "onboard_state": "State (राज्य)",
        "onboard_craft": "Craft Details",
        "onboard_fabric": "Fabric Speciality",
        "onboard_weave": "Weave Style (बुनाई शैली)",
        "onboard_min_price": "Minimum Order Price (₹)",
        "onboard_delivery": "Typical Delivery Days",
        "onboard_verification": "Verification",
        "onboard_aadhaar": "Aadhaar Last 4 Digits",
        "onboard_bank": "Bank Account Number (for payments)",
        "onboard_whatsapp": "I have WhatsApp on this number and can receive order notifications",
        "onboard_custom": "I can accept custom / made-to-order requests",
        "onboard_consent": "I agree to list on Meesho through the Pakshi network",
        "onboard_lang": "Preferred Language for Notifications",
        "onboard_photo": "Upload a sample of your work (optional)",
        "onboard_submit": "Submit Profile — Join Pakshi Network",
        "onboard_speak": "🎤 Speak Your Registration (बोलकर भरें)",
        "onboard_gps": "📍 Get Current Location",
        "ooak_title": "♻️ One of a Kind — Wholesale Resale Outlet",
        "ooak_empty": "No rejected pieces yet — that is a good sign. When a custom order does not meet a buyer's expectation, it lands here at wholesale price. No waste. No loss.",
        "ooak_ready": "ready to ship",
        "common_authentic": "✓ Authentic Handloom",
        "common_master_artisan": "Master Artisan",
        "common_delivery": "Delivery",
        "common_rating": "Rating",
        "common_cancel": "Order Cancelled. Piece moved to Wholesale Outlet.",
        "common_approved": "Fabric Approved! {weaver} is shipping your order.",
    },
    "hi": {
        "app_title": "पक्षी — हथकरघा डायरेक्ट",
        "tagline": "भारत के मास्टर बुनकरों से सीधे · बिना बिचौलिए के",
        "meesho_badge": "🪢 मीशो वेरिफाइड मेड-टू-ऑर्डर हथकरघा वर्टिकल",
        "trust_banner": "✅ 100% हथकरघा प्रमाणित · 💵 कैश ऑन डिलीवरी उपलब्ध · 🚚 डायरेक्ट फैक्ट्री शिपिंग",
        "nav_buyer": "खरीदार पोर्टल",
        "nav_weaver": "बुनकर डैशबोर्ड",
        "nav_ooak": "एक तरह का",
        "nav_onboard": "बुनकर पंजीकरण",
        "step_start": "शुरू",
        "step_intent": "इरादा बताएं",
        "step_swatch": "स्वैच चुनें",
        "step_lock": "फैब्रिक लॉक करें",
        "step_confirm": "ऑर्डर कन्फर्म",
        "btn_select": "विकल्प चुनें",
        "btn_confirm": "ऑर्डर कन्फर्म करें",
        "btn_back": "चयन पर वापस जाएं",
        "btn_new_search": "✨ नई साड़ी खोज शुरू करें",
        "btn_yes_alt": "✅ हाँ, विकल्प दिखाएँ",
        "btn_no_alt": "❌ नहीं, मूल विनिर्देश रखें",
        "btn_cancel_order": "❌ ऑर्डर रद्द करें",
        "btn_approve": "✅ स्वीकार करें और भेजें",
        "btn_reject": "❌ टुकड़ा अस्वीकार करें",
        "btn_buy_now": "अभी खरीदें",
        "section_swatches": "🎨 अनुशंसित कारीगर स्वैच",
        "section_orders": "📦 आपके सक्रिय ऑर्डर",
        "agent_thinking": "⏳ एजेंट आपके लिए मेल खाते कारीगरों को ढूंढ रहा है...",
        "order_status_production": "उत्पादन में",
        "order_status_approval": "अनुमोदन की प्रतीक्षा",
        "order_status_completed": "पूर्ण",
        "order_status_photo_sent": "फोटो भेजा — अनुमोदन की प्रतीक्षा",
        "weaver_dashboard_title": "🧑‍🎨 बुनकर पोर्टल",
        "weaver_min_base": "🛡️ न्यूनतम मूल्य सीमा",
        "weaver_audio_mode": "🔊 हैंड्स-फ्री लूम ऑडियो मोड",
        "weaver_voice_controls": "🎙️ वॉइस लूम कंट्रोल (हाथों के बिना काम करें)",
        "weaver_voice_caption": "कहें 'पहला ऑर्डर स्वीकार करो', 'ऑर्डर 2847 मना करो', या 'बायर को दिखाओ' (फोटो भेजने के लिए)।",
        "weaver_read_orders": "मेरे ऑर्डर पढ़कर सुनाएँ",
        "weaver_pending": "📥 लंबित प्रसारण",
        "weaver_production": "🧵 उत्पादन में (लूम पर)",
        "weaver_awaiting": "⏳ खरीदार की मंजूरी की प्रतीक्षा",
        "weaver_simulate": "📡 नया आने वाला प्रसारण अनुकरण करें",
        "weaver_accept": "✅ स्वीकार करें",
        "weaver_decline": "❌ अस्वीकार करें",
        "weaver_send_photo": "खरीदार की मंजूरी के लिए फोटो भेजें",
        "onboard_title": "बुनकर पंजीकरण — पक्षी नेटवर्क से जुड़ें",
        "onboard_desc": "मीशो द्वारा संचालित — एक बार पंजीकरण पूरा होने पर, आपकी प्रोफ़ाइल पक्षी नेटवर्क पर लाइव हो जाती है। खरीदार बताते हैं कि उन्हें क्या चाहिए, एजेंट आपसे मिलान करता है, और ऑर्डर सीधे आपके फोन पर आते हैं। कोई बिचौलिया नहीं। आपकी कारीगरी। आपकी कीमत।",
        "onboard_submitted": "✅ प्रोफ़ाइल लाइव!",
        "onboard_go_dashboard": "बुनकर डैशबोर्ड पर जाएँ",
        "onboard_register_another": "दूसरा बुनकर पंजीकृत करें",
        "onboard_basic": "मूल विवरण",
        "onboard_name": "पूरा नाम",
        "onboard_phone": "मोबाइल / व्हाट्सएप नंबर",
        "onboard_cluster": "गाँव / क्लस्टर",
        "onboard_state": "राज्य",
        "onboard_craft": "कारीगरी विवरण",
        "onboard_fabric": "फैब्रिक विशेषता",
        "onboard_weave": "बुनाई शैली",
        "onboard_min_price": "न्यूनतम ऑर्डर मूल्य (₹)",
        "onboard_delivery": "सामान्य डिलीवरी दिन",
        "onboard_verification": "सत्यापन",
        "onboard_aadhaar": "आधार अंतिम 4 अंक",
        "onboard_bank": "बैंक खाता संख्या (भुगतान के लिए)",
        "onboard_whatsapp": "मेरे पास इस नंबर पर व्हाट्सएप है और मैं ऑर्डर सूचनाएँ प्राप्त कर सकता हूँ",
        "onboard_custom": "मैं कस्टम / मेड-टू-ऑर्डर अनुरोध स्वीकार कर सकता हूँ",
        "onboard_consent": "मैं पक्षी नेटवर्क के माध्यम से मीशो पर सूचीबद्ध होने के लिए सहमत हूँ",
        "onboard_lang": "सूचनाओं के लिए पसंदीदा भाषा",
        "onboard_photo": "अपने काम का नमूना अपलोड करें (वैकल्पिक)",
        "onboard_submit": "प्रोफ़ाइल सबमिट करें — पक्षी नेटवर्क से जुड़ें",
        "onboard_speak": "🎤 अपना पंजीकरण बोलकर भरें",
        "onboard_gps": "📍 वर्तमान स्थान प्राप्त करें",
        "ooak_title": "♻️ एक तरह का — थोक पुनर्विक्रय आउटलेट",
        "ooak_empty": "अभी तक कोई अस्वीकृत टुकड़ा नहीं — यह अच्छा संकेत है। जब कोई कस्टम ऑर्डर खरीदार की अपेक्षा पर खरा नहीं उतरता, तो यह थोक मूल्य पर यहाँ आता है। कोई बर्बादी नहीं, कोई नुकसान नहीं।",
        "ooak_ready": "शिप करने के लिए तैयार",
        "common_authentic": "✓ प्रामाणिक हथकरघा",
        "common_master_artisan": "मास्टर कारीगर",
        "common_delivery": "डिलीवरी",
        "common_rating": "रेटिंग",
        "common_cancel": "ऑर्डर रद्द कर दिया गया। टुकड़ा थोक आउटलेट में स्थानांतरित कर दिया गया।",
        "common_approved": "फैब्रिक स्वीकृत! {weaver} आपका ऑर्डर शिप कर रहा है।",
    }
}

def get_ui_string(key: str, lang: str = "en") -> str:
    lang = lang if lang in UI_STRINGS else "en"
    return UI_STRINGS[lang].get(key, UI_STRINGS["en"].get(key, key))

# ---------------------------------------------------------------------------
# CSS (full, with fixes for mobile)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg-deep:        #fef3f0;
    --bg-surface:     #ffffff;
    --bg-card:        #fff5f2;
    --bg-card-2:      #ffded5;
    --accent:         #F43397;
    --accent-hover:   #d4287f;
    --accent-glow:    rgba(244,51,151,0.25);
    --text-primary:   #2d2d2d;
    --text-muted:     #6b6b6b;
    --text-white:     #ffffff;
    --success:        #22c55e;
    --warning:        #f59e0b;
    --danger:         #ef4444;
    --border:         rgba(0,0,0,0.08);
    --border-strong:  rgba(0,0,0,0.15);
}

html, body { background-color: var(--bg-deep) !important; }
.stApp { background-color: var(--bg-deep) !important; font-family: 'Inter', sans-serif !important; }
.main .block-container {
    padding: 1rem 1.2rem 3rem !important;
    max-width: 100% !important;
    background-color: var(--bg-deep) !important;
}
section[data-testid="stSidebar"] { background-color: var(--bg-surface) !important; }
#MainMenu, footer, header { visibility: hidden !important; }

p, li, span, label { color: var(--text-primary); font-family: 'Inter', sans-serif !important; }
h1, h2, h3 { color: var(--text-primary) !important; font-family: 'Inter', sans-serif !important; }

.wordmark {
    font-size: 2rem; font-weight: 800;
    color: var(--text-primary); letter-spacing: -0.5px; line-height: 1.1;
}
.wordmark span { color: var(--accent); }
.tagline {
    font-size: 0.85rem; color: var(--text-muted);
    margin-top: 2px; margin-bottom: 0; letter-spacing: 0.02em;
}
.meesho-badge {
    font-size: 0.70rem; color: var(--text-white);
    background: var(--accent);
    border: none;
    padding: 4px 14px; border-radius: 999px;
    display: inline-block; margin-top: 6px;
    letter-spacing: 0.05em; font-weight: 700;
}

.trust-banner {
    display: flex; gap: 1rem; align-items: center; justify-content: space-around;
    background: rgba(244,51,151,0.06); border: 1px solid rgba(244,51,151,0.2);
    border-radius: 10px; padding: 0.6rem 1rem; margin-bottom: 1.2rem;
    font-size: 0.80rem; color: var(--text-primary); font-weight: 600; text-align: center;
}

.card {
    background: var(--bg-surface);
    border: 1px solid var(--border-strong);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.9rem;
    color: var(--text-primary);
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.card:hover { transform: translateY(-2px); box-shadow: 0 8px 28px rgba(0,0,0,0.08); }

.swatch-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-strong);
    border-radius: 12px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.6rem;
}
.swatch-price { font-size: 1.5rem; font-weight: 800; color: var(--accent); line-height: 1.1; }
.swatch-label {
    font-size: 0.68rem; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.1em;
    margin-top: 0.7rem; margin-bottom: 0.1rem;
}
.swatch-value { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); }

.tag {
    display: inline-block; padding: 4px 10px; border-radius: 999px;
    background: var(--accent); color: var(--text-white);
    font-size: 0.75rem; font-weight: 600; margin: 2px 2px 0 0;
    border: none;
}
.tag-warning {
    display: inline-block; padding: 4px 10px; border-radius: 999px;
    background: var(--warning); color: var(--text-white);
    font-size: 0.75rem; font-weight: 700; margin: 2px 2px 0 0;
    border: none;
}

.chat-wrap { display: flex; flex-direction: column; gap: 0.3rem; padding-bottom: 0.5rem; }
.bubble-agent {
    background: var(--bg-surface);
    border: 1px solid var(--border-strong);
    border-radius: 14px 14px 14px 3px;
    padding: 0.8rem 1rem;
    max-width: 86%;
    font-size: 0.95rem; line-height: 1.6;
    white-space: pre-wrap; color: var(--text-primary);
    align-self: flex-start;
}
.bubble-user {
    background: var(--accent);
    border: none;
    border-radius: 14px 14px 3px 14px;
    padding: 0.8rem 1rem;
    max-width: 74%;
    font-size: 0.95rem; line-height: 1.6;
    color: var(--text-white);
    align-self: flex-end; text-align: right;
}

.step-row { display: flex; align-items: center; gap: 0.55rem; font-size: 0.85rem; }
.step-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.step-dot.done    { background: var(--success); }
.step-dot.active  { background: var(--accent); box-shadow: 0 0 6px var(--accent-glow); }
.step-dot.pending { background: #ddd; opacity: 0.4; }

.stButton > button {
    background: var(--accent) !important;
    color: var(--text-white) !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.7rem 1.4rem !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 1rem !important;
    transition: opacity 0.15s, box-shadow 0.15s !important;
    letter-spacing: 0.01em !important;
    min-height: 48px;
}
.stButton > button:hover { opacity: 0.88 !important; box-shadow: 0 0 18px var(--accent-glow) !important; }
.stButton > button:active { opacity: 0.75 !important; }

.stTextInput input,
.stTextArea textarea {
    background-color: var(--bg-surface) !important;
    color: var(--text-primary) !important;
    border: 1.5px solid var(--border-strong) !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 1rem !important;
    padding: 0.7rem !important;
    caret-color: var(--accent) !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(255,107,107,0.2) !important;
    outline: none !important;
}

@media (max-width: 768px) {
    .main .block-container { padding: 0.6rem 0.6rem 2rem !important; }
    .wordmark { font-size: 1.4rem; }
    .tagline { font-size: 0.72rem; }
    .bubble-agent, .bubble-user { font-size: 0.88rem; max-width: 98%; padding: 0.6rem 0.8rem; }
    .swatch-card { padding: 0.6rem 0.7rem; }
    .swatch-price { font-size: 1.15rem; }
    .stButton > button { font-size: 0.92rem !important; padding: 0.65rem 0.8rem !important; min-height: 48px; width: 100%; }
    .step-row { font-size: 0.72rem; gap: 0.25rem; }
    .tag { font-size: 0.65rem; padding: 2px 7px; }
    .trust-banner { flex-direction: column; gap: 0.2rem; font-size: 0.68rem; padding: 0.4rem; }
    div[role="radiogroup"] { gap: 0.25rem !important; flex-wrap: wrap !important; }
    div[role="radiogroup"] label { padding: 0.35rem 0.65rem !important; font-size: 0.72rem !important; }
    .card, .order-card { padding: 0.75rem 0.85rem; border-radius: 10px; }
    img { max-width: 100% !important; height: auto !important; }
    [data-testid="column"] { min-width: 100% !important; }
    .section-label { font-size: 0.65rem; }
    audio { width: 100% !important; }
}
@media (max-width: 480px) {
    .wordmark { font-size: 1.2rem; }
    .swatch-price { font-size: 1rem; }
    .bubble-agent, .bubble-user { font-size: 0.82rem; }
    .meesho-badge { font-size: 0.62rem; padding: 3px 10px; }
}
.divider { height: 1px; background: var(--border); margin: 1rem 0; }
.order-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-strong);
    border-radius: 12px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.7rem;
    transition: transform 0.15s ease;
}
.order-card:hover { transform: translateY(-1px); }
.order-card.below-base { border-color: var(--warning); background: rgba(245,158,11,0.04); }
.order-card.accepted { border-color: var(--success); }
.section-label {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--accent);
    margin-bottom: 0.35rem;
    margin-top: 0.1rem;
}
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
# Edge TTS & STT
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

        async def _run_and_read():
            path = await generate()
            with open(path, "rb") as fh:
                return fh.read()
        return asyncio.run(_run_and_read())
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
# Command parsers
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
# Helper to parse onboarding details from voice transcript
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Session state initializers
# ---------------------------------------------------------------------------
def _init_buyer_state() -> None:
    defaults = {
        "agent": None, "history": [], "current_state": "greeting", "swatches": [],
        "selected_swatch": None, "order": None, "agent_data": {}, "awaiting": None,
        "reasoning_log": [], "one_of_a_kind": [], "buyer_orders": [], "agent_thinking": False,
        "prefill_text": "", "greeted": False, "last_buyer_audio_hash": None,
        "language": "en",
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def _init_weaver_state() -> None:
    if "weaver_orders" not in st.session_state: st.session_state["weaver_orders"] = _make_demo_orders()
    if "weaver_id" not in st.session_state: st.session_state["weaver_id"] = "W001"
    if "min_base_price" not in st.session_state: st.session_state["min_base_price"] = 1000
    if "audio_work_mode" not in st.session_state: st.session_state["audio_work_mode"] = False
    if "last_weaver_audio_hash" not in st.session_state: st.session_state["last_weaver_audio_hash"] = None
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

def _get_all_weavers() -> list:
    builtin = _load_weaver_profiles()
    custom = st.session_state.get("custom_weavers", [])
    return builtin + custom

# ---------------------------------------------------------------------------
# Header & UI Elements
# ---------------------------------------------------------------------------
def _render_header() -> None:
    lang = st.session_state.get("language", "en")
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'padding:0.5rem 0 0.8rem;border-bottom:1px solid rgba(240,188,212,0.10);margin-bottom:1rem;">'
        f'<div>'
        f'<div class="wordmark">Pak<span>shi</span> 🪶</div>'
        f'<div class="tagline">{get_ui_string("tagline", lang)}</div>'
        f'<div class="meesho-badge">{get_ui_string("meesho_badge", lang)}</div>'
        f'</div>'
        f'<div style="font-size:0.75rem;color:rgba(240,188,212,0.4);font-weight:600;text-align:right;">'
        f'100% ARTISAN DIRECT<br><span style="color:#22c55e;">CASH ON DELIVERY AVAILABLE</span>'
        f'</div></div>', unsafe_allow_html=True,
    )

_STATE_STEPS_EN = [
    ("greeting", "Start"), ("collecting", "Describe Intent"), ("retrieved", "Select Swatch"),
    ("fallback_pending", "Fallback"), ("swatch_selected", "Lock Fabric"),
    ("broadcasting", "Broadcast"), ("weaver_selected", "Matched"), ("confirmed", "Order Placed"),
]
_STATE_STEPS_HI = [
    ("greeting", "शुरू"), ("collecting", "इरादा बताएं"), ("retrieved", "स्वैच चुनें"),
    ("fallback_pending", "फॉलबैक"), ("swatch_selected", "फैब्रिक लॉक करें"),
    ("broadcasting", "प्रसारण"), ("weaver_selected", "मेल"), ("confirmed", "ऑर्डर कन्फर्म"),
]
_HIDDEN_STATES = {"fallback_pending", "broadcasting", "weaver_selected"}

def _step_indicator(current: str) -> None:
    lang = st.session_state.get("language", "en")
    steps = _STATE_STEPS_HI if lang.startswith("hi") else _STATE_STEPS_EN
    active = next((i for i, (k, _) in enumerate(steps) if k == current), 0)
    parts = ['<div style="display:flex;gap:1.2rem;align-items:center;margin-bottom:1rem;flex-wrap:wrap;">']
    for i, (key, label) in enumerate(steps):
        if key in _HIDDEN_STATES: continue
        cls = "done" if i < active else ("active" if i == active else "pending")
        color = "#22c55e" if cls == "done" else ("var(--accent)" if cls == "active" else "var(--text-muted)")
        parts.append(
            f'<div class="step-row"><div class="step-dot {cls}"></div>'
            f'<span style="font-size:0.80rem;color:{color};font-weight:600;">{label}</span></div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Swatch card (using HTML with unsafe_allow_html=True)
# ---------------------------------------------------------------------------
def _swatch_card(swatch: dict, index: int) -> None:
    lang = st.session_state.get("language", "en")
    tags = "".join(f'<span class="tag">{t}</span>' for t in swatch.get("sensory_tags", [])[:3])
    location = swatch.get("weaver_state", "")
    if swatch.get("weaver_cluster"):
        location = f"{swatch.get('weaver_cluster')}, {location}"

    html = f"""
    <div class="swatch-card" style="border: 1.5px solid {'var(--accent)' if index == 0 else 'var(--border-strong)'};">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span style="background:var(--bg-card);color:var(--text-primary);padding:2px 8px;border-radius:6px;font-size:0.75rem;font-weight:700;">{get_ui_string('common_authentic', lang)}</span>
        </div>
        <div style="background:rgba(218,65,103,0.08);border:1px dashed rgba(218,65,103,0.3);border-radius:8px;padding:12px;font-size:0.78rem;color:var(--text-muted);text-align:center;">Fabric swatch image will appear here</div>
        <div style="font-weight:800;font-size:1.05rem;color:var(--text-primary);margin-bottom:2px;">
            {swatch.get('weave_style','—')}
        </div>
        <div style="font-size:0.85rem;color:var(--text-muted);margin-bottom:6px;">
            {swatch.get('color','—')} · <span style="color:var(--accent);font-weight:600;">{location}</span>
        </div>
        <div class="swatch-price">₹{swatch.get('price_inr','?')}</div>
        <div style="font-size:0.72rem;color:var(--text-muted);margin-bottom:6px;">Includes weaver labor & direct home delivery</div>
        <div style="font-size:0.80rem;color:var(--text-primary);line-height:1.55;margin-bottom:6px;opacity:0.9;">
            {swatch.get('description', '')}
        </div>
        <div style="margin:6px 0;">{tags}</div>
        <div class="divider"></div>
        <div class="swatch-label">{get_ui_string('common_master_artisan', lang)}</div>
        <div class="swatch-value">{swatch.get('weaver_name','—')}</div>
        <div style="font-size:0.80rem;color:var(--text-muted);">{location}</div>
        <div style="margin-top:4px;font-size:0.82rem;color:var(--text-primary);font-weight:600;">
            ⭐ {get_ui_string('common_rating', lang)}: {swatch.get('weaver_rating','?')} &nbsp;·&nbsp;  {get_ui_string('common_delivery', lang)}: {swatch.get('delivery_days','?')} days
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Core send function
# ---------------------------------------------------------------------------
def _send(user_text: str, *, force_new_search: bool = False) -> None:
    user_text = (user_text or "").strip()
    if not user_text:
        return

    PakshiAgent, err = _load_agent_class()
    if err or PakshiAgent is None:
        st.error(f"Backend not loaded: {err}")
        return

    if force_new_search:
        st.session_state["swatches"] = []
        st.session_state["agent_data"] = {}
        st.session_state["current_state"] = "collecting"
        st.session_state["agent"] = None

    if st.session_state.get("agent") is None:
        try:
            st.session_state["agent"] = PakshiAgent()
        except Exception as exc:
            st.error(f"Agent init failed: {exc}")
            return

    # Avoid duplicate history entries
    if st.session_state["history"] and st.session_state["history"][-1][0] == "user" and st.session_state["history"][-1][1] == user_text:
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

    msg = response.get("message", "") if isinstance(response, dict) else str(response)
    state = response.get("state", "greeting") if isinstance(response, dict) else "greeting"
    data = response.get("data", {}) if isinstance(response, dict) else {}

    # Language detection based on Devanagari script
    if any('\u0900' <= c <= '\u097F' for c in user_text):
        st.session_state["language"] = "hi"
    else:
        st.session_state["language"] = "en"

    st.session_state["current_state"] = state
    st.session_state["history"].append(("agent", msg))
    st.session_state["agent_data"] = data

    # Replace swatches, don't append
    if data.get("swatches"):
        st.session_state["swatches"] = data["swatches"]
    if data.get("order"):
        st.session_state["order"] = data["order"]

    if state == "confirmed" and data.get("order"):
        raw = data["order"]
        sw, wv = raw.get("selected_swatch") or {}, raw.get("selected_weaver") or {}
        entry = {
            "order_id": raw.get("order_id", "PKS-???"),
            "weave_style": sw.get("weave_style", "—"),
            "color": sw.get("color", "—"),
            "price": sw.get("price_inr", 0),
            "weaver_name": wv.get("weaver_name", "—"),
            "status": "In Production",
            "photo_path": None,
        }
        existing_ids = {o["order_id"] for o in st.session_state.get("buyer_orders", [])}
        if entry["order_id"] not in existing_ids:
            st.session_state["buyer_orders"].append(entry)

    if state in ("fallback_pending", "broadcasting", "weaver_selected", "confirmed"):
        snippet = msg[:120] + ("..." if len(msg) > 120 else "")
        st.session_state["reasoning_log"].append(f"[{state.upper()}] {snippet}")

# ---------------------------------------------------------------------------
# BUYER PAGE
# ---------------------------------------------------------------------------
def _buyer_page() -> None:
    _init_buyer_state()
    lang = st.session_state.get("language", "en")
    st.markdown(f'<div class="trust-banner">{get_ui_string("trust_banner", lang)}</div>', unsafe_allow_html=True)

    if st.session_state.get("agent_thinking"):
        st.markdown(f'<div style="background:rgba(255,107,107,0.12);border-left:4px solid var(--accent);padding:0.8rem 1rem;border-radius:0 8px 8px 0;font-size:0.90rem;font-weight:600;color:var(--text-primary);margin-bottom:0.8rem;">{get_ui_string("agent_thinking", lang)}</div>', unsafe_allow_html=True)

    buyer_orders = st.session_state.get("buyer_orders", [])
    if buyer_orders:
        with st.expander(f"{get_ui_string('section_orders', lang)} ({len(buyer_orders)})", expanded=True):
            for bo in buyer_orders:
                status = bo.get("status", "In Production")
                color = {"In Production": "var(--warning)", "Awaiting Approval": "var(--accent)", "Completed": "#22c55e", "Photo Sent — Awaiting Approval": "var(--accent)"}.get(status, "var(--text-muted)")
                needs_approval = status in ("Awaiting Approval", "Photo Sent — Awaiting Approval")
                photo_html = f'<div style="margin-top:10px;"><div style="background:rgba(218,65,103,0.08);border:1px dashed rgba(218,65,103,0.3);border-radius:8px;padding:12px;font-size:0.78rem;color:var(--text-muted);text-align:center;">Fabric swatch image will appear here</div></div>' if bo.get("photo_path") else ""

                status_label = get_ui_string(f"order_status_{status.lower().replace(' ', '_')}", lang) if status.lower().replace(' ', '_') in ["in_production", "awaiting_approval", "completed", "photo_sent_awaiting_approval"] else status
                if status == "In Production": status_label = get_ui_string("order_status_production", lang)
                elif status == "Awaiting Approval": status_label = get_ui_string("order_status_approval", lang)
                elif status == "Completed": status_label = get_ui_string("order_status_completed", lang)
                elif status == "Photo Sent — Awaiting Approval": status_label = get_ui_string("order_status_photo_sent", lang)

                st.markdown(f"""
                <div style="background:var(--bg-surface);border:1px solid var(--border-strong);border-radius:10px;padding:1rem;margin-bottom:0.5rem;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;">
                        <div>
                            <div style="font-weight:800;font-size:1rem;color:var(--text-primary);">{bo["weave_style"]} · {bo["color"]}</div>
                            <div style="font-size:0.80rem;color:var(--text-muted);">#{bo["order_id"]} · Artisan: {bo["weaver_name"]} · ₹{bo["price"]:,}</div>
                            {photo_html}
                        </div>
                        <div style="background:rgba(0,0,0,0.05);padding:4px 12px;border-radius:999px;font-size:0.75rem;font-weight:700;color:{color};">{status_label}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if needs_approval:
                    st.markdown(f"""
                    <div style="background:rgba(255,107,107,0.08);border:2px solid var(--accent);border-radius:12px;padding:1rem;margin:0.6rem 0;">
                        <div style="font-weight:700;font-size:0.95rem;color:var(--text-primary);margin-bottom:4px;">Your fabric is ready for review</div>
                        <div style="font-size:0.82rem;color:var(--text-muted);">The artisan has finished weaving. Approve to ship or reject to move it to the One of a Kind resale outlet at 65% of the original price.</div>
                    </div>
                    """, unsafe_allow_html=True)
                    a1, a2, _ = st.columns([1, 1, 2])
                    with a1:
                        if st.button(get_ui_string("btn_approve", lang), key=f"app_{bo['order_id']}", use_container_width=True):
                            bo["status"] = "Completed"
                            for wo in st.session_state.get("weaver_orders", []):
                                if wo["order_id"] == bo["order_id"]:
                                    wo["status"] = "completed"
                            st.success(get_ui_string("common_approved", lang).format(weaver=bo["weaver_name"]))
                            st.rerun()
                            return
                    with a2:
                        if st.button(get_ui_string("btn_reject", lang), key=f"rej_{bo['order_id']}", use_container_width=True):
                            st.session_state.setdefault("one_of_a_kind", []).append({
                                "order_id": bo["order_id"],
                                "weave_style": bo["weave_style"],
                                "color": bo["color"],
                                "original_price": bo["price"],
                                "resale_price": int(bo["price"] * 0.65),
                                "weaver_name": bo["weaver_name"],
                                "reason": "Buyer rejected final fabric",
                            })
                            st.session_state["buyer_orders"].remove(bo)
                            for wo in st.session_state.get("weaver_orders", []):
                                if wo["order_id"] == bo["order_id"]:
                                    wo["status"] = "declined"
                            st.warning(get_ui_string("common_cancel", lang))
                            st.rerun()
                            return

                if status == "In Production":
                    if st.button(get_ui_string("btn_cancel_order", lang), key=f"cancel_{bo['order_id']}", use_container_width=True):
                        st.session_state.setdefault("one_of_a_kind", []).append({
                            "order_id": bo["order_id"],
                            "weave_style": bo["weave_style"],
                            "color": bo["color"],
                            "original_price": bo["price"],
                            "resale_price": int(bo["price"] * 0.65),
                            "weaver_name": bo["weaver_name"],
                            "reason": "Buyer cancelled before production",
                        })
                        st.session_state["buyer_orders"].remove(bo)
                        for wo in st.session_state.get("weaver_orders", []):
                            if wo["order_id"] == bo["order_id"]:
                                wo["status"] = "declined"
                        st.warning(get_ui_string("common_cancel", lang))
                        st.rerun()
                        return

    _step_indicator(st.session_state["current_state"])
    col_chat, col_panel = st.columns([3, 2], gap="large")

    with col_panel:
        swatches = st.session_state.get("swatches", [])
        if swatches:
            st.markdown(f'<div class="section-label">{get_ui_string("section_swatches", lang)}</div>', unsafe_allow_html=True)
            for i, sw in enumerate(swatches[:3]):
                _swatch_card(sw, i)
                if st.session_state["current_state"] == "retrieved":
                    if st.button(f"{get_ui_string('btn_select', lang)} {i+1}", key=f"sel_{i}", use_container_width=True):
                        _send(str(i + 1))
                        st.rerun()
                        return
            if st.session_state["current_state"] == "retrieved":
                st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
                if st.button(get_ui_string("btn_new_search", lang), use_container_width=True, key="none_of_these"):
                    _send("search again", force_new_search=True)
                    st.rerun()
                    return

    with col_chat:
        if st.session_state["history"]:
            bubbles = ""
            for role, text in st.session_state["history"]:
                cls = "bubble-agent" if role == "agent" else "bubble-user"
                text_escaped = text.replace("<", "&lt;").replace(">", "&gt;")
                bubbles += f'<div class="{cls}">{text_escaped}</div>'
            st.markdown(f'<div class="chat-wrap">{bubbles}</div>', unsafe_allow_html=True)

        cur = st.session_state["current_state"]
        if cur == "fallback_pending":
            c1, c2 = st.columns(2)
            if c1.button(get_ui_string("btn_yes_alt", lang), use_container_width=True):
                _send("yes")
                st.rerun()
                return
            if c2.button(get_ui_string("btn_no_alt", lang), use_container_width=True):
                _send("no")
                st.rerun()
                return
        elif cur == "swatch_selected":
            c1, c2 = st.columns(2)
            if c1.button(get_ui_string("btn_confirm", lang), use_container_width=True):
                _send("confirm")
                st.rerun()
                return
            if c2.button(get_ui_string("btn_back", lang), use_container_width=True):
                _send("back")
                st.rerun()
                return
        elif cur in ("confirmed", "failed"):
            if st.button(get_ui_string("btn_new_search", lang), use_container_width=True):
                for k in list(st.session_state.keys()):
                    if k not in ("one_of_a_kind", "buyer_orders", "weaver_orders", "weaver_id", "min_base_price", "audio_work_mode", "custom_weavers", "language"):
                        del st.session_state[k]
                st.rerun()
                return
        else:
            if cur == "greeting" and not st.session_state["history"] and not st.session_state["greeted"]:
                st.session_state["greeted"] = True
                _send("hi")
                st.rerun()
                return

            # ---- BUYER AUDIO INPUT (with hash guard) ----
            st.markdown(f'<div class="section-label">{get_ui_string("onboard_speak", lang)}</div>', unsafe_allow_html=True)
            audio_file = st.audio_input("Record", label_visibility="collapsed", key="pakshi_buyer_audio")
            if audio_file is not None:
                _b_hash = hash(bytes(audio_file.getbuffer()))
                if st.session_state.get("last_buyer_audio_hash") != _b_hash:
                    st.session_state["last_buyer_audio_hash"] = _b_hash
                    with st.spinner("Transcribing..."):
                        text, err = _transcribe_audio(audio_file)
                    if err:
                        st.warning(err)
                    else:
                        t = text.lower().strip()
                        nmap = {"one":"1","two":"2","three":"3","first":"1","second":"2","third":"3",
                                "ek":"1","do":"2","teen":"3","pehla":"1","doosra":"2","teesra":"3"}
                        if t in nmap and cur == "retrieved":
                            _send(nmap[t])
                        elif _is_correction(t) and cur == "retrieved":
                            _send(t, force_new_search=True)
                        else:
                            _send(text)
                    st.rerun()
                    return

            # ---- STABLE TEXT INPUT ----
            st.text_input("Type your message...", key="user_input", label_visibility="collapsed")
            if st.button(get_ui_string("btn_select", lang), key="send_btn", use_container_width=True):
                ui = st.session_state.get("user_input", "").strip()
                if ui:
                    if cur == "retrieved" and not _is_number_selection(ui):
                        _send(ui, force_new_search=True)
                    else:
                        _send(ui)
                    st.session_state["user_input"] = ""  # clear after send
                    st.rerun()
                    return

# ---------------------------------------------------------------------------
# WEAVER PAGE (bilingual, audio controls)
# ---------------------------------------------------------------------------
def _weaver_page() -> None:
    _init_weaver_state()
    all_weavers = _get_all_weavers()
    lang = st.session_state.get("language", "en")
    st.markdown(f'<div class="section-label">{get_ui_string("weaver_dashboard_title", lang)}</div>', unsafe_allow_html=True)

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
        st.markdown(f"**{get_ui_string('weaver_min_base', lang)}**")
        st.session_state["min_base_price"] = st.number_input("Min Base Price (₹)", min_value=500, max_value=15000, step=100, value=st.session_state["min_base_price"], label_visibility="collapsed")
    with c_audio:
        st.markdown(f"**{get_ui_string('weaver_audio_mode', lang)}**")
        st.session_state["audio_work_mode"] = st.toggle("Enable Hindi Announcements", value=st.session_state["audio_work_mode"])

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown(f'<div class="section-label">{get_ui_string("weaver_voice_controls", lang)}</div>', unsafe_allow_html=True)
    st.caption(get_ui_string("weaver_voice_caption", lang))

    # -------- AUDIO INPUT SECTION (debugged) --------
    w_audio = st.audio_input("Record Weaver Command", label_visibility="collapsed", key="pakshi_weaver_audio")
    orders = st.session_state.get("weaver_orders", [])
    pending = [o for o in orders if o.get("status") == "pending"]
    accepted = [o for o in orders if o.get("status") == "accepted"]

    if w_audio is not None:
        _w_hash = hash(bytes(w_audio.getbuffer()))
        # Only process if new audio or we explicitly allow reprocessing
        if st.session_state.get("last_weaver_audio_hash") != _w_hash:
            st.session_state["last_weaver_audio_hash"] = _w_hash
            with st.spinner("Sun rahe hain..."):
                try:
                    text, err = _transcribe_audio(w_audio)
                except Exception as e:
                    text, err = None, f"Transcription error: {e}"
            
            # DEBUG: show raw text
            st.write(f"**DEBUG:** Raw transcript = `{text}`" if text else "**DEBUG:** No transcript received.")

            if err:
                st.warning(f"Transcription failed: {err}")
                # Reset hash so the user can try the same clip again
                st.session_state["last_weaver_audio_hash"] = None
            else:
                # ----- SIMPLE, RELIABLE PARSING (inline) -----
                cmd = None
                text_lower = text.lower()
                
                # 1. Try to find an order ID (numeric part)
                import re
                ids_in_text = re.findall(r'\b(\d{4})\b', text_lower)  # finds 4-digit numbers
                
                # If no 4-digit, look for words like "first", "second", "pehla"
                if not ids_in_text:
                    if any(w in text_lower for w in ["first", "pehla", "1st"]):
                        if pending:
                            target_id = pending[0].get("order_id")
                    elif any(w in text_lower for w in ["second", "doosra", "2nd"]) and len(pending) > 1:
                        target_id = pending[1].get("order_id")
                    else:
                        target_id = None
                else:
                    # Match the first numeric ID found against our orders
                    numeric_id = ids_in_text[0]
                    # Try to find any order containing this number
                    for o in orders:
                        if numeric_id in o.get("order_id", ""):
                            target_id = o["order_id"]
                            break
                    else:
                        target_id = None

                # 2. Determine action
                action = None
                if any(w in text_lower for w in ["accept", "swikaar", "sweekar", "accept karo", "haan"]):
                    action = "accept"
                elif any(w in text_lower for w in ["decline", "mana", "reject", "na karo", "no"]):
                    action = "decline"
                elif any(w in text_lower for w in ["show", "photo", "tasveer", "send", "bhejo"]):
                    action = "show_buyer"
                else:
                    action = None

                if action and target_id:
                    cmd = {"action": action, "order_id": target_id}
                else:
                    cmd = {"action": "error", "message": f"Could not understand. Heard: '{text}'. Try 'accept order 2847' or 'decline first order'."}

                # DEBUG: show parsed command
                st.write(f"**DEBUG:** Parsed command = {cmd}")

                if cmd and cmd.get("action") != "error":
                    act, oid = cmd["action"], cmd["order_id"]
                    idx = next((i for i, o in enumerate(orders) if o["order_id"] == oid), None)
                    if idx is not None:
                        # --- Perform the action ---
                        if act == "accept":
                            orders[idx]["status"] = "accepted"
                            for bo in st.session_state.get("buyer_orders", []):
                                if bo["order_id"] == oid:
                                    bo["status"] = "In Production"
                            st.session_state["weaver_orders"] = orders
                            st.session_state["buyer_orders"] = st.session_state.get("buyer_orders", [])
                            st.success(f"✅ Accepted {oid}!")
                            try:
                                if ab := _tts_bytes(f"Order {oid[-4:]} swikaar ho gaya.", lang="hi"):
                                    _autoplay_audio(ab)
                            except Exception as e:
                                st.warning(f"Audio announcement skipped: {e}")
                            st.rerun()
                            return
                        elif act == "decline":
                            orders[idx]["status"] = "declined"
                            for bo in st.session_state.get("buyer_orders", []):
                                if bo["order_id"] == oid:
                                    bo["status"] = "Declined"
                            st.session_state["weaver_orders"] = orders
                            st.session_state["buyer_orders"] = st.session_state.get("buyer_orders", [])
                            st.warning(f"❌ Declined {oid}.")
                            try:
                                if ab := _tts_bytes(f"Order {oid[-4:]} mana kar diya.", lang="hi"):
                                    _autoplay_audio(ab)
                            except Exception as e:
                                st.warning(f"Audio announcement skipped: {e}")
                            st.rerun()
                            return
                        elif act == "show_buyer":
                            orders[idx]["status"] = "awaiting_approval"
                            orders[idx]["photo"] = "loom_snapshot_auto.jpg"
                            for bo in st.session_state.get("buyer_orders", []):
                                if bo["order_id"] == oid:
                                    bo["status"] = "Awaiting Approval"
                                    bo["photo_path"] = "loom_snapshot_auto.jpg"
                            st.session_state["weaver_orders"] = orders
                            st.session_state["buyer_orders"] = st.session_state.get("buyer_orders", [])
                            st.success(f"📸 Photo sent for {oid}.")
                            try:
                                if ab := _tts_bytes(f"Fabric tayyar hai. Buyer ko tasveer bhej di gayi.", lang="hi"):
                                    _autoplay_audio(ab)
                            except Exception as e:
                                st.warning(f"Audio announcement skipped: {e}")
                            st.rerun()
                            return
                    else:
                        st.error(f"Order {oid} not found in your list.")
                else:
                    msg = cmd.get("message", "Command not recognised.")
                    st.warning(msg)
                    st.caption("Try: 'accept first order' or 'decline order 2847' or 'show order 2847'")
            
            st.rerun()
            return

    # -------- READ ORDERS AUDIO BUTTON (debugged) --------
    if st.session_state.get("audio_work_mode") and (pending or accepted):
        if st.button(get_ui_string("weaver_read_orders", lang), use_container_width=False, key="read_orders_btn"):
            lines = []
            if pending:
                lines.append(f"Aapke paas {len(pending)} naye order hain.")
                for o in pending[:3]:
                    lines.append(
                        f"Order {o.get('order_id','')[-4:]}: "
                        f"{o.get('weave_style','fabric')}, "
                        f"keemat {o.get('price',0)} rupaye."
                    )
            if accepted:
                lines.append(f"{len(accepted)} order loom par chal rahe hain.")
            full_text = " ".join(lines)
            try:
                if ab := _tts_bytes(full_text, lang="hi"):
                    _autoplay_audio(ab, label="Your orders summary")
            except Exception as e:
                st.warning(f"TTS error: {e}")

    # -------- PENDING ORDERS (buttons) --------
    if pending:
        st.markdown(f'<div class="section-label" style="margin-top:1rem;">{get_ui_string("weaver_pending", lang)}</div>', unsafe_allow_html=True)
        for order in pending:
            idx = next((i for i, o in enumerate(orders) if o.get("order_id") == order.get("order_id")), None)
            is_below = int(order.get("price",0)) < st.session_state["min_base_price"]
            badge = f'<span class="tag-warning">⚠️ Below Base (₹{st.session_state["min_base_price"]})</span>' if is_below else '<span class="tag">✓ Meets Base</span>'
            st.markdown(f"""
            <div class="order-card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div><div style="font-weight:800;font-size:1.05rem;color:var(--text-primary);">{order.get("weave_style","—")}</div>
                         <div style="font-size:0.80rem;color:var(--text-muted);">#{order.get("order_id","—")} · {badge}</div></div>
                    <div class="swatch-price">₹{order.get("price",0):,}</div>
                </div>
            </div>""", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            if b1.button(get_ui_string("weaver_accept", lang), key=f"acc_{order['order_id']}", use_container_width=True):
                orders[idx]["status"] = "accepted"
                for bo in st.session_state.get("buyer_orders", []):
                    if bo["order_id"] == order["order_id"]:
                        bo["status"] = "In Production"
                st.session_state["weaver_orders"] = orders
                st.session_state["buyer_orders"] = st.session_state.get("buyer_orders", [])
                try:
                    if ab := _tts_bytes("Order swikaar kiya", lang="hi"):
                        _autoplay_audio(ab)
                except Exception:
                    pass
                st.rerun()
                return
            if b2.button(get_ui_string("weaver_decline", lang), key=f"dec_{order['order_id']}", use_container_width=True):
                orders[idx]["status"] = "declined"
                for bo in st.session_state.get("buyer_orders", []):
                    if bo["order_id"] == order["order_id"]:
                        bo["status"] = "Declined"
                st.session_state["weaver_orders"] = orders
                st.session_state["buyer_orders"] = st.session_state.get("buyer_orders", [])
                st.rerun()
                return

    # -------- ACCEPTED ORDERS (photo upload) --------
    if accepted:
        st.markdown(f'<div class="section-label" style="margin-top:1rem;">{get_ui_string("weaver_production", lang)}</div>', unsafe_allow_html=True)
        for order in accepted:
            idx = next((i for i, o in enumerate(orders) if o.get("order_id") == order.get("order_id")), None)
            st.markdown(f"""
            <div class="order-card accepted">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div><div style="font-weight:700;font-size:0.95rem;color:var(--text-primary);">{order.get("weave_style","—")}</div>
                         <div style="font-size:0.80rem;color:var(--text-muted);">#{order.get("order_id","—")}</div></div>
                    <div class="state-badge state-active">{get_ui_string("order_status_production", lang)}</div>
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
            if st.button(f"{get_ui_string('weaver_send_photo', lang)} — #{order['order_id']}", key=f"show_{order['order_id']}"):
                photo_name = uploaded.name if uploaded else "loom_snapshot.jpg"
                orders[idx]["status"] = "awaiting_approval"
                orders[idx]["photo"] = photo_name
                for bo in st.session_state.get("buyer_orders", []):
                    if bo["order_id"] == order["order_id"]:
                        bo["status"] = "Awaiting Approval"
                        bo["photo_path"] = photo_name
                st.session_state["weaver_orders"] = orders
                st.session_state["buyer_orders"] = st.session_state.get("buyer_orders", [])
                st.success(f"Photo sent for #{order['order_id']}.")
                st.rerun()
                return

    # -------- AWAITING APPROVAL --------
    awaiting = [o for o in orders if o.get("status") == "awaiting_approval"]
    if awaiting:
        st.markdown(f'<div class="section-label" style="margin-top:1rem;">{get_ui_string("weaver_awaiting", lang)}</div>', unsafe_allow_html=True)
        for order in awaiting:
            st.info(f"Order #{order['order_id']} is pending approval from the buyer.")

    st.markdown('<div style="height:1.2rem;"></div>', unsafe_allow_html=True)
    if st.button(get_ui_string("weaver_simulate", lang), use_container_width=True):
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
            try:
                if ab := _tts_bytes(f"Naya order aaya hai! Keemat {new_order['price']} rupaye.", lang="hi"):
                    _autoplay_audio(ab)
            except Exception:
                pass
        st.rerun()
        return
# ---------------------------------------------------------------------------
# ONE OF A KIND PAGE
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
    lang = st.session_state.get("language", "en")
    st.markdown(f'<div class="section-label">{get_ui_string("ooak_title", lang)}</div>', unsafe_allow_html=True)
    if "ooak_seeded" not in st.session_state:
        existing_ids = {i.get("order_id") for i in st.session_state.get("one_of_a_kind", [])}
        for seed in _OOAK_SEED:
            if seed["order_id"] not in existing_ids:
                st.session_state.setdefault("one_of_a_kind", []).append(seed)
        st.session_state["ooak_seeded"] = True

    items = st.session_state.get("one_of_a_kind", [])
    if not items:
        st.markdown(f"""
        <div class="card" style="text-align:center;padding:2rem;">
            <div style="font-size:0.95rem;font-weight:700;margin-bottom:0.4rem;">{get_ui_string('ooak_empty', lang)}</div>
        </div>""", unsafe_allow_html=True)
        return

    st.caption(f"{len(items)} unique handwoven piece{'s' if len(items)>1 else ''} at wholesale prices — ready to ship.")
    for idx, item in enumerate(items):
        orig, resale = item.get("original_price", 0), item.get("resale_price", 0)
        discount = int((1 - resale / orig) * 100) if orig else 0
        tags_html = "".join(f'<span class="tag">{t}</span>' for t in item.get("sensory_tags", [])[:3])
        col_card, col_btn = st.columns([5, 1], gap="small")
        with col_card:
            # FIX: use var(--text-primary) for title
            st.markdown(f"""
            <div class="card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;">
                    <div>
                        <div style="font-weight:800;font-size:1.05rem;color:var(--text-primary);">
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
                            <span class="tag" style="background:rgba(34,197,94,0.15);color:#22c55e;">{get_ui_string('ooak_ready', lang)}</span>
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
            if st.button(get_ui_string("btn_buy_now", lang), key=f"buy_{item.get('order_id',idx)}_{idx}", use_container_width=True):
                st.success(f"#{item.get('order_id','')} added to cart. Delivery in 3-5 days.")

# ---------------------------------------------------------------------------
# WEAVER ONBOARDING PAGE (bilingual, voice extraction, GPS)
# ---------------------------------------------------------------------------
def _onboarding_page() -> None:
    # ---- Parser function embedded inside ----
    def _parse_onboarding_text(text: str) -> dict:
        # Known weaving clusters (from weaver_profiles.json)
        KNOWN_CLUSTERS = [
            "pochampally", "venkatagiri", "kanchipuram", "ilkal", "kota", "chanderi",
            "maheshwar", "dharmavaram", "mysore", "sambalpuri", "bagru", "sanganer",
            "kutch", "kerala", "tamil nadu", "andhra pradesh", "telangana", "karnataka",
            "rajasthan", "west bengal", "odisha", "gujarat", "maharashtra", "bihar",
            "uttar pradesh", "varanasi", "banaras", "kashi", "paithani", "yeola",
            "molakalmuru", "uppada", "nuapatna", "arni", "balaramapuram", "coimbatore",
            "salem", "bishnupur", "murshidabad", "shantipur", "bhagalpur"
        ]
        
        # Define these at the top so they're always available
        english_weaves = [
            "ikat", "jamdani", "block print", "banarasi", "kanjivaram",
            "tussar", "chanderi", "maheshwari", "paithani", "patola",
            "kota doria", "sambalpuri", "ilkal", "venkatagiri", "zari", "kasavu"
        ]
        
        weave_map = {
            "टिकट": "ikat", "इकट": "ikat",
            "बनारसी": "banarasi", "कांचीपुरम": "kanjivaram",
            "जामदानी": "jamdani", "तुस्सर": "tussar",
            "चंदेरी": "chanderi", "महेश्वरी": "maheshwari",
            "पैठणी": "paithani", "पटोला": "patola",
            "कोटा डोरिया": "kota doria", "संबलपुरी": "sambalpuri",
            "इलकल": "ilkal", "वेंकटागिरी": "venkatagiri",
            "जरी": "zari", "कसावु": "kasavu"
        }
        
        result = {"name": "", "cluster": "", "specialty": "", "phone": ""}
        
        # Clean and normalize
        t = text.lower().strip()
        t = re.sub(r'[.,;:!?]', ' ', t)
        t = re.sub(r'\s+', ' ', t)
        
        # 1. PHONE (10-digit number, tolerates spaces/dashes in speech)
        clean_digits = re.sub(r'\D', '', t)
        phone_match = re.search(r'(\d{10})', clean_digits)
        if phone_match:
            result["phone"] = phone_match.group(1)
        
        # 2. SPECIALTY (weave)
        for hindi, eng in weave_map.items():
            if hindi in t:
                result["specialty"] = eng.title()
                break
        if not result["specialty"]:
            for w in english_weaves:
                if w in t:
                    result["specialty"] = w.title()
                    break
        
        # 3. CLUSTER / VILLAGE
        # 3a. Known clusters first
        cluster_found = None
        for cluster in KNOWN_CLUSTERS:
            if cluster in t:
                cluster_found = cluster.title()
                break
        if cluster_found:
            result["cluster"] = cluster_found
        
        # 3b. Unknown village fallback via contextual patterns
        if not result["cluster"]:
            # Build exclusion set – now english_weaves is defined
            english_weaves_lower = [w.lower() for w in english_weaves]
            weave_values_lower = [v.lower() for v in weave_map.values()]
            stopwords = {
                "main", "mera", "my", "name", "naam", "hai", "is", "hoon", "hun",
                "है", "मैं", "हूँ", "से", "ki", "की", "में", "ka", "का", "ke", "के",
                "hu", "hain", "ho", "raha", "rahi", "banati", "banata", "banate",
                "number", "phone", "mobile", "gav", "gaon", "village", "cluster",
                "weave", "weaver", "bunkar", "karigar", "specialty", "speciality",
                "from", "of", "in", "live", "stay", "at", "i", "am", "meri", "मेरी"
            }
            exclusion_set = set(stopwords) | set(english_weaves_lower) | set(weave_values_lower)
            
            village_patterns = [
                r'(?:main|mera|मैं|मेरा)\s+([a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+){0,2})\s+(?:se|से)\s+(?:hun|hoon|hain|हूँ|हैं|है|raha|रहा|rahi|रही)',
                r'([a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+)?)\s+(?:gaon|गांव|village)',
                r'(?:gaon|गांव|village)\s+([a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+)?)',
                r'(?:from|of|in)\s+([a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+){0,2})',
                r'(?:live|stay)\s+(?:in|at)\s+([a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+){0,2})',
                r'(?:mera|मेरा)\s+(?:gaon|गांव|village)\s+([a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+)?)\s+(?:hai|है)',
                r'([a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+)?)\s+(?:ki|की|ka|का|ke|के)\s+(?:ikat|इकट|jamdani|जामदानी|banarasi|बनारसी|chanderi|चंदेरी|maheshwari|महेश्वरी|paithani|पैठणी|patola|पटोला|tussar|तुस्सर|zari|जरी|kasavu|कसावु)',
                r'([a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+)?)\s+(?:ikat|इकट|jamdani|जामदानी|banarasi|बनारसी|chanderi|चंदेरी|maheshwari|महेश्वरी)\s+(?:banati|बनाती|banata|बनाता|banate|बनाते)',
            ]
            
            for pattern in village_patterns:
                match = re.search(pattern, t, re.IGNORECASE)
                if match:
                    candidate = match.group(1).strip().lower()
                    cand_words = [w for w in candidate.split()
                                  if w not in exclusion_set and len(w) > 2]
                    if cand_words:
                        result["cluster"] = " ".join(cand_words).title()
                        break
        
        # 4. NAME
        name_found = None
        
        # 4a. Explicit name markers first
        name_markers = [
            r'(?:mera|मेरा|my)\s+(?:naam|name)\s+([a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+)?)',
            r'(?:naam|name)\s+(?:hai|is)\s+([a-zA-Z\u0900-\u097F]+(?:\s+[a-zA-Z\u0900-\u097F]+)?)',
        ]
        for pattern in name_markers:
            match = re.search(pattern, t, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if len(candidate) > 1 and not candidate.isdigit():
                    name_found = candidate.title()
                    break
        
        # 4b. Residual word approach
        if not name_found:
            name_text = t
            
            # Remove phone digits
            if result["phone"]:
                name_text = re.sub(r'\d', ' ', name_text)
            
            # Remove cluster / village
            if result["cluster"]:
                name_text = name_text.replace(result["cluster"].lower(), " ")
            
            # Remove specialty (English + Hindi equivalents)
            if result["specialty"]:
                spec_lower = result["specialty"].lower()
                name_text = name_text.replace(spec_lower, " ")
                for hindi, eng in weave_map.items():
                    if eng.lower() == spec_lower:
                        name_text = name_text.replace(hindi, " ")
            
            # Remove stopwords
            stopwords_set = {
                "main", "mera", "my", "name", "naam", "hai", "is", "hoon", "hun",
                "है", "मैं", "हूँ", "से", "ki", "की", "में", "ka", "का", "ke", "के",
                "number", "phone", "hu", "hain", "ho", "raha", "rahi", "banati", "banata"
            }
            for sw in stopwords_set:
                name_text = re.sub(r'(?:^|\s)' + re.escape(sw) + r'(?:\s|$)', ' ', name_text, flags=re.IGNORECASE)
            
            name_text = re.sub(r'\s+', ' ', name_text).strip()
            
            if name_text:
                words = [w for w in name_text.split() if len(w) > 1]
                if words:
                    name_found = " ".join(words[:2]).title()
        
        result["name"] = name_found or ""
        
        # 4c. Final fallback: first meaningful word not used by cluster/specialty
        if not result["name"]:
            words = t.split()
            stopwords_fb = {
                "main", "mera", "my", "name", "naam", "hai", "is", "hoon", "hun",
                "है", "मैं", "हूँ", "से", "ki", "की", "में", "ka", "का", "ke", "के",
                "number", "phone", "hu", "hain", "ho", "raha", "rahi", "banati", "banata"
            }
            for i, w in enumerate(words):
                w_clean = w.strip('.,;:!?')
                w_lower = w_clean.lower()
                if (w_lower not in stopwords_fb and not w_clean.isdigit() and len(w_clean) > 1 and
                    not (result["cluster"] and w_lower in result["cluster"].lower()) and
                    not (result["specialty"] and w_lower in result["specialty"].lower())):
                    name_candidate = w_clean.title()
                    if i + 1 < len(words):
                        next_w = words[i+1].strip('.,;:!?')
                        next_lower = next_w.lower()
                        if (next_lower not in stopwords_fb and not next_w.isdigit() and len(next_w) > 1 and
                            not (result["cluster"] and next_lower in result["cluster"].lower()) and
                            not (result["specialty"] and next_lower in result["specialty"].lower())):
                            name_candidate += " " + next_w.title()
                    result["name"] = name_candidate
                    break
        
        return result

    # ---- END OF PARSER ----
    
    lang = st.session_state.get("language", "en")
    st.markdown(f'<div class="section-label">{get_ui_string("onboard_title", lang)}</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:rgba(245,166,35,0.08);border:1px solid rgba(245,166,35,0.25);
        border-radius:10px;padding:0.75rem 1rem;margin-bottom:1rem;font-size:0.82rem;
        color:var(--text-primary);line-height:1.6;">
        {get_ui_string("onboard_desc", lang)}
    </div>
    """, unsafe_allow_html=True)

    # Ensure state keys exist
    if "onboard_submitted" not in st.session_state:
        st.session_state["onboard_submitted"] = False
    if "onboard_data" not in st.session_state:
        st.session_state["onboard_data"] = {}
    if "reg_name" not in st.session_state:
        st.session_state["reg_name"] = ""
    if "reg_cluster" not in st.session_state:
        st.session_state["reg_cluster"] = ""
    if "reg_specialty" not in st.session_state:
        st.session_state["reg_specialty"] = ""
    if "reg_phone" not in st.session_state:
        st.session_state["reg_phone"] = ""
    if "last_reg_audio_hash" not in st.session_state:
        st.session_state["last_reg_audio_hash"] = None

    if st.session_state["onboard_submitted"]:
        d = st.session_state["onboard_data"]
        st.markdown(f"""
        <div style="background:rgba(34,197,94,0.08);border:1.5px solid #22c55e;
            border-radius:12px;padding:1.4rem;text-align:center;margin-top:1rem;">
            <div style="font-size:1.3rem;font-weight:800;color:#22c55e;margin-bottom:0.4rem;">
                {get_ui_string("onboard_submitted", lang)}
            </div>
            <div style="font-size:0.85rem;color:var(--text-primary);line-height:1.7;">
                <strong>{d.get("name","")}</strong> registered successfully.<br>
                {get_ui_string("onboard_cluster", lang)}: {d.get("cluster","")} · {get_ui_string("onboard_fabric", lang)}: {d.get("fabric","")}<br>
                <span style="color:var(--accent);font-weight:600;">
                Confirmation will be sent to {d.get("phone","")} via WhatsApp.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(get_ui_string("onboard_go_dashboard", lang), use_container_width=True):
            st.session_state["onboard_submitted"] = False
            st.session_state["onboard_data"] = {}
            st.query_params.update({"tab": "Weaver Dashboard"})
            st.rerun()

        _oid = d.get("id", "") or st.session_state.get("weaver_id", "")
        if _oid:
            st.success(f"Weaver ID: {_oid} — Switch to 'Weaver Dashboard' tab. Your profile is now in the dropdown and can receive orders immediately.")
        
        _oc1, _oc2 = st.columns(2)
        if _oc1.button(get_ui_string("onboard_register_another", lang), use_container_width=True):
            st.session_state["onboard_submitted"] = False
            st.session_state["onboard_data"] = {}
            st.rerun()

        if _oc2.button("Go to Weaver Dashboard", use_container_width=True):
            st.session_state["onboard_submitted"] = False
            st.session_state["onboard_data"] = {}
            st.query_params["tab"] = "Weaver Dashboard"
            st.rerun()

    # GPS location button
    if st.button(get_ui_string("onboard_gps", lang), use_container_width=False):
        gps_js = """
        <script>
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    const lat = pos.coords.latitude;
                    const lon = pos.coords.longitude;
                    const url = new URL(window.location.href);
                    url.searchParams.set('lat', lat);
                    url.searchParams.set('lon', lon);
                    window.location.href = url.toString();
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

    # Handle GPS query params safely
    try:
        lat = st.query_params.get("lat")
        lon = st.query_params.get("lon")
        if isinstance(lat, list):
            lat = lat[0] if lat else None
        if isinstance(lon, list):
            lon = lon[0] if lon else None
    except Exception:
        lat = lon = None

    if lat and lon:
        st.session_state["gps_coords"] = f"{lat}, {lon}"
        try:
            resp = requests.get(
                f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=10",
                headers={"User-Agent": "Pakshi-Hackathon"},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if "display_name" in data:
                    place = data["display_name"].split(",")[0].strip()
                    st.session_state["gps_place"] = place
        except Exception:
            pass
        
        try:
            if "lat" in st.query_params:
                del st.query_params["lat"]
            if "lon" in st.query_params:
                del st.query_params["lon"]
        except Exception:
            pass
        
        st.rerun()

    # Voice input with template guidance
    st.markdown(f"""
    <div style="background:rgba(244,51,151,0.07);border:2px solid rgba(244,51,151,0.35);
        border-radius:14px;padding:1rem 1.2rem;margin-bottom:1rem;">
        <div style="font-weight:700;font-size:1rem;color:var(--text-primary);margin-bottom:4px;">
            {get_ui_string('onboard_speak', lang)}
        </div>
        <div style="font-size:0.82rem;color:var(--text-muted);line-height:1.6;">
            <strong>Please say your name, village, weave, and phone number.</strong><br>
            Example: <em>"अनिका पोचमपल्ली टिकट 1234567891"</em><br>
            Or: <em>"main shruti pochampally ki hun ikat banati hun number 9876543210"</em>
        </div>
    </div>
    """, unsafe_allow_html=True)

    reg_audio = st.audio_input("Speak to fill the form", key="reg_audio", label_visibility="collapsed")
    if reg_audio is not None:
        _audio_hash = hash(bytes(reg_audio.getbuffer()))
        if st.session_state.get("last_reg_audio_hash") != _audio_hash:
            st.session_state["last_reg_audio_hash"] = _audio_hash
            with st.spinner("Listening and extracting details..."):
                text, err = _transcribe_audio(reg_audio)
            if err:
                st.warning(f"Could not transcribe: {err}. Please type the details below.")
            else:
                st.markdown(
                    f'<div style="background:rgba(34,197,94,0.08);border:1px solid #22c55e;'
                    f'border-radius:8px;padding:0.6rem 1rem;font-size:0.85rem;margin-bottom:0.5rem;">'
                    f'Heard: <em>{text}</em></div>',
                    unsafe_allow_html=True
                )
                parsed = _parse_onboarding_text(text)
                filled = [k for k, v in parsed.items() if v]
                for key, val in parsed.items():
                    if val:
                        st.session_state[f"reg_{key}"] = val
                if filled:
                    st.success(f"Auto-filled: {', '.join(filled)}. Review and correct below.")
                else:
                    st.warning("Could not extract details from the audio. Please type the fields manually.")
            st.rerun()

    # Display the form with pre-filled values from session state
    with st.form("onboard_form"):
        st.markdown(f'<div class="section-label">{get_ui_string("onboard_basic", lang)}</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        default_name = st.session_state.get("reg_name", "")
        default_cluster = st.session_state.get("gps_place", "") or st.session_state.get("reg_cluster", "")
        default_specialty = st.session_state.get("reg_specialty", "")
        default_phone = st.session_state.get("reg_phone", "")

        name = c1.text_input(get_ui_string("onboard_name", lang), value=default_name, placeholder="e.g. Padmavathi Devi")
        phone = c2.text_input(get_ui_string("onboard_phone", lang), value=default_phone, placeholder="10-digit number")

        c3, c4 = st.columns(2)
        cluster = c3.text_input(get_ui_string("onboard_cluster", lang), value=default_cluster, placeholder="e.g. Pochampally")
        state = c4.selectbox(get_ui_string("onboard_state", lang), [
            "Andhra Pradesh", "Bihar", "Gujarat", "Jharkhand", "Karnataka",
            "Kerala", "Madhya Pradesh", "Maharashtra", "Odisha", "Rajasthan",
            "Tamil Nadu", "Telangana", "Uttar Pradesh", "West Bengal", "Other"
        ])

        st.markdown(f'<div class="section-label" style="margin-top:0.8rem;">{get_ui_string("onboard_craft", lang)}</div>', unsafe_allow_html=True)
        c5, c6 = st.columns(2)
        fabric = c5.multiselect(get_ui_string("onboard_fabric", lang), ["Cotton", "Silk", "Cotton-Silk", "Tussar", "Linen"])
        weave = c6.text_input(get_ui_string("onboard_weave", lang), value=default_specialty, placeholder="e.g. Ikat, Jamdani, Block Print")

        c7, c8 = st.columns(2)
        min_p = c7.number_input(get_ui_string("onboard_min_price", lang), min_value=300, max_value=50000, value=1000, step=100)
        delivery = c8.number_input(get_ui_string("onboard_delivery", lang), min_value=3, max_value=60, value=14, step=1)

        st.markdown(f'<div class="section-label" style="margin-top:0.8rem;">{get_ui_string("onboard_verification", lang)}</div>', unsafe_allow_html=True)
        c9, c10 = st.columns(2)
        aadhaar = c9.text_input(get_ui_string("onboard_aadhaar", lang), placeholder="XXXX", max_chars=4)
        bank = c10.text_input(get_ui_string("onboard_bank", lang), placeholder="Account number")

        whatsapp = st.checkbox(get_ui_string("onboard_whatsapp", lang))
        custom = st.checkbox(get_ui_string("onboard_custom", lang))
        consent = st.checkbox(get_ui_string("onboard_consent", lang))

        lang_pref = st.selectbox(get_ui_string("onboard_lang", lang), [
            "Hindi", "Telugu", "Tamil", "Kannada", "Bengali", "Gujarati", "Marathi", "English"
        ])

        photo = st.file_uploader(get_ui_string("onboard_photo", lang), type=["jpg","jpeg","png"])
        if photo:
            st.image(photo, caption="Sample work preview", width=260)

        submitted = st.form_submit_button(get_ui_string("onboard_submit", lang), use_container_width=True)

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
                new_id = f"CW{random.randint(100,999)}"
                
                photo_bytes = None
                if photo is not None:
                    photo_bytes = photo.getvalue()
                
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
                    "language": lang_pref,
                    "photo": photo_bytes,
                }
                st.session_state.setdefault("custom_weavers", []).append(new_profile)
                st.session_state.setdefault("live_weavers", []).append(new_profile)
                st.session_state["weaver_id"] = new_id

                st.session_state["onboard_data"] = {
                    "id": new_id,
                    "name": name.strip(),
                    "phone": phone.strip(),
                    "cluster": cluster.strip(),
                    "state": state,
                    "fabric": ", ".join(fabric),
                    "weave": weave.strip(),
                    "min_price": min_p,
                    "delivery_days": delivery,
                    "whatsapp": whatsapp,
                    "accepts_custom": custom,
                    "language": lang_pref,
                }
                st.session_state["onboard_submitted"] = True
                st.rerun()
# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if "language" not in st.session_state:
        st.session_state["language"] = "en"

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

    default_tab = 0
    tab_param = st.query_params.get("tab")
    if tab_param:
        if "Buyer" in tab_param:
            default_tab = 0
        elif "Weaver Dashboard" in tab_param:
            default_tab = 1
        elif "One of a Kind" in tab_param or "Wholesale" in tab_param:
            default_tab = 2
        elif "Weaver Onboarding" in tab_param:
            default_tab = 3
        st.query_params.clear()

    lang = st.session_state.get("language", "en")
    tab_keys = ["buyer", "weaver", "ooak", "onboard"]
    tab_labels = [
        get_ui_string("nav_buyer", lang),
        get_ui_string("nav_weaver", lang),
        get_ui_string("nav_ooak", lang),
        get_ui_string("nav_onboard", lang),
    ]

    selected_label = st.radio(
        "Nav",
        tab_labels,
        horizontal=True,
        label_visibility="collapsed",
        index=default_tab,
    )
    selected_key = tab_keys[tab_labels.index(selected_label)]

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    if selected_key == "buyer":
        _buyer_page()
    elif selected_key == "weaver":
        _weaver_page()
    elif selected_key == "onboard":
        _onboarding_page()
    else:
        _ooak_page()

if __name__ == "__main__":
    main()
