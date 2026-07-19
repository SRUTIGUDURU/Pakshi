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
from typing import Optional, Tuple

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
# UI Language Strings  (ALL labels bilingual)
# ---------------------------------------------------------------------------
UI_STRINGS = {
    "en": {
        "app_title": "Pakshi — Handloom Direct",
        "tagline": "Direct from India's Master Weavers · Zero Middlemen Markup",
        "meesho_badge": "Meesho Verified Made-to-Order Handloom Vertical",
        "trust_banner": "100% Handloom Verified · Pay on Delivery Available · Direct Factory Shipping",
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
        "section_swatches": "Recommended Artisanal Swatches",
        "section_orders": "Your Active Orders",
        "agent_thinking": "Agent is finding matching artisans for you...",
        "order_status_production": "In Production",
        "order_status_approval": "Awaiting Approval",
        "order_status_completed": "Completed",
        "order_status_photo_sent": "Photo Sent — Awaiting Approval",
        "weaver_dashboard_title": "Artisan Portal",
        "weaver_min_base": "Minimum Base Price Threshold",
        "weaver_audio_mode": "🔊 Hands-Free Loom Audio Mode",
        "weaver_voice_controls": "🎙️ Voice Loom Controls (work without hands)",
        "weaver_voice_caption": "Say 'Accept first order', 'Reject order 2847', or 'Show buyer' (send photo).",
        "weaver_read_orders": "Read My Orders Aloud",
        "weaver_pending": "Pending Broadcasts",
        "weaver_production": "In Production (On Loom)",
        "weaver_awaiting": "Awaiting Buyer Approval",
        "weaver_simulate": "Simulate New Incoming Broadcast",
        "weaver_accept": "✅ Accept",
        "weaver_decline": "❌ Decline",
        "weaver_send_photo": "Send Photo for Buyer Approval",
        "onboard_title": "Weaver Onboarding — Join the Pakshi Network",
        "onboard_desc": "Powered by Meesho — Once you complete onboarding, your weaver profile goes live on the Pakshi network. Buyers describe what they want, the agent matches you, and orders come directly to your phone. No middlemen. Your craft. Your price.",
        "onboard_submitted": "✅ Profile Live!",
        "onboard_go_dashboard": "Go to Weaver Dashboard",
        "onboard_register_another": "Register Another Weaver",
        "onboard_basic": "Basic Details",
        "onboard_name": "Full Name",
        "onboard_phone": "Mobile / WhatsApp Number",
        "onboard_cluster": "Village / Cluster",
        "onboard_state": "State",
        "onboard_craft": "Craft Details",
        "onboard_fabric": "Fabric Speciality",
        "onboard_weave": "Weave Style",
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
        "onboard_speak": "🎤 Speak Your Registration",
        "onboard_gps": "Get Current Location",
        "ooak_title": "One of a Kind — Wholesale Resale Outlet",
        "ooak_empty": "No rejected pieces yet — that is a good sign. When a custom order does not meet a buyer's expectation, it lands here at wholesale price. No waste. No loss.",
        "ooak_ready": "ready to ship",
        "common_authentic": "✓ Authentic Handloom",
        "common_master_artisan": "Master Artisan",
        "common_delivery": "Delivery",
        "common_rating": "Rating",
        "common_cancel": "Order Cancelled. Piece moved to Wholesale Outlet.",
        "common_approved": "Fabric Approved! {weaver} is shipping your order.",
        "swatch_labor": "Includes weaver labor & direct home delivery",
        "swatch_placeholder": "Fabric swatch image will appear here",
        "type_message": "Type your message...",
        "send_btn": "Send",
        "transcribing": "Transcribing...",
        "heard": "Heard",
        "select_option": "Select Option",
        "none_of_these": "✨ None of these — Search Again",
        "below_base": "⚠️ Below Base",
        "meets_base": "✓ Meets Base",
        "deliver_by": "Deliver by",
        "photo_sent": "📸 Fabric photo received — preview not available in demo mode",
        "fabric_ready": "Your fabric is ready for review",
        "fabric_ready_desc": "The artisan has finished weaving. Approve to ship or reject to move it to the One of a Kind resale outlet at 65% of the original price.",
        "order_added": "added to cart. Delivery in 3-5 days.",
        "warming_up": "Agent is warming up on first load — this takes about 15 seconds. Subsequent responses will be instant.",
        "upload_photo": "Upload progress photo",
        "photo_sent_success": "Photo sent for #{oid}. Buyer will be notified.",
        "awaiting_approval_msg": "Order #{oid} is pending approval from the buyer.",
        "tip_audio": "Tip: If audio keeps failing, install pydub for WebM support: pip install pydub",
        "cmd_not_recognised": "Command not recognised. Heard: \"{text}\". Say 'accept' to accept, 'decline' to decline, or 'show buyer' to send photo.",
        "no_pending": "No pending orders to act on.",
        "no_production": "No in-production orders to act on.",
        "order_accepted": "✅ Accepted {oid}!",
        "order_declined": "❌ Declined {oid}. Moved to wholesale outlet.",
        "photo_sent_buyer": "📸 Photo sent to buyer for #{oid}.",
        "pieces_label": "unique handwoven pieces at wholesale prices — ready to ship.",
        "piece_label": "unique handwoven piece at wholesale price — ready to ship.",
        "woven_by": "Woven by",
        "reason_label": "Rejected:",
        "original_price": "Original",
    },
    "hi": {
        "app_title": "पक्षी — हथकरघा डायरेक्ट",
        "tagline": "भारत के मास्टर बुनकरों से सीधे · बिना बिचौलिए के",
        "meesho_badge": "मीशो वेरिफाइड मेड-टू-ऑर्डर हथकरघा वर्टिकल",
        "trust_banner": "100% हथकरघा प्रमाणित · कैश ऑन डिलीवरी उपलब्ध · डायरेक्ट फैक्ट्री शिपिंग",
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
        "section_swatches": "अनुशंसित कारीगर स्वैच",
        "section_orders": "आपके सक्रिय ऑर्डर",
        "agent_thinking": "एजेंट आपके लिए मेल खाते कारीगरों को ढूंढ रहा है...",
        "order_status_production": "उत्पादन में",
        "order_status_approval": "अनुमोदन की प्रतीक्षा",
        "order_status_completed": "पूर्ण",
        "order_status_photo_sent": "फोटो भेजा — अनुमोदन की प्रतीक्षा",
        "weaver_dashboard_title": "बुनकर पोर्टल",
        "weaver_min_base": "न्यूनतम मूल्य सीमा",
        "weaver_audio_mode": "🔊 हैंड्स-फ्री लूम ऑडियो मोड",
        "weaver_voice_controls": "🎙️ वॉइस लूम कंट्रोल (हाथों के बिना काम करें)",
        "weaver_voice_caption": "कहें 'पहला ऑर्डर स्वीकार करो', 'ऑर्डर 2847 मना करो', या 'बायर को दिखाओ'।",
        "weaver_read_orders": "मेरे ऑर्डर पढ़कर सुनाएँ",
        "weaver_pending": "लंबित प्रसारण",
        "weaver_production": "उत्पादन में (लूम पर)",
        "weaver_awaiting": "खरीदार की मंजूरी की प्रतीक्षा",
        "weaver_simulate": "नया आने वाला प्रसारण अनुकरण करें",
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
        "onboard_speak": "🎤 बोलकर फॉर्म भरें",
        "onboard_gps": "वर्तमान स्थान प्राप्त करें",
        "ooak_title": "एक तरह का — थोक पुनर्विक्रय आउटलेट",
        "ooak_empty": "अभी तक कोई अस्वीकृत टुकड़ा नहीं — यह अच्छा संकेत है। जब कोई कस्टम ऑर्डर खरीदार की अपेक्षा पर खरा नहीं उतरता, तो यह थोक मूल्य पर यहाँ आता है। कोई बर्बादी नहीं, कोई नुकसान नहीं।",
        "ooak_ready": "शिप करने के लिए तैयार",
        "common_authentic": "✓ प्रामाणिक हथकरघा",
        "common_master_artisan": "मास्टर कारीगर",
        "common_delivery": "डिलीवरी",
        "common_rating": "रेटिंग",
        "common_cancel": "ऑर्डर रद्द कर दिया गया। टुकड़ा थोक आउटलेट में स्थानांतरित कर दिया गया।",
        "common_approved": "फैब्रिक स्वीकृत! {weaver} आपका ऑर्डर शिप कर रहा है।",
        "swatch_labor": "बुनकर की मेहनत और घर पर डिलीवरी सहित",
        "swatch_placeholder": "फैब्रिक स्वैच इमेज यहाँ दिखेगी",
        "type_message": "अपना संदेश टाइप करें...",
        "send_btn": "भेजें",
        "transcribing": "ट्रांसक्राइब हो रहा है...",
        "heard": "सुना",
        "select_option": "विकल्प चुनें",
        "none_of_these": "✨ इनमें से कोई नहीं — फिर खोजें",
        "below_base": "⚠️ न्यूनतम से कम",
        "meets_base": "✓ न्यूनतम से ऊपर",
        "deliver_by": "डिलीवरी तक",
        "photo_sent": "📸 फैब्रिक फोटो मिली — डेमो में प्रीव्यू उपलब्ध नहीं",
        "fabric_ready": "आपका कपड़ा समीक्षा के लिए तैयार है",
        "fabric_ready_desc": "कारीगर ने बुनाई पूरी कर ली है। शिप करने के लिए स्वीकार करें या एक तरह के आउटलेट में 65% मूल्य पर भेजें।",
        "order_added": "कार्ट में जोड़ा गया। 3-5 दिन में डिलीवरी।",
        "warming_up": "एजेंट पहली बार लोड हो रहा है — इसमें लगभग 15 सेकंड लगते हैं। बाद के जवाब तुरंत आएंगे।",
        "upload_photo": "प्रगति फोटो अपलोड करें",
        "photo_sent_success": "#{oid} का फोटो भेज दिया गया। खरीदार को सूचित किया जाएगा।",
        "awaiting_approval_msg": "ऑर्डर #{oid} खरीदार की मंजूरी का इंतज़ार कर रहा है।",
        "tip_audio": "सुझाव: यदि ऑडियो काम नहीं कर रहा, pydub इंस्टॉल करें: pip install pydub",
        "cmd_not_recognised": "कमांड समझ नहीं आई। सुना: \"{text}\"। 'स्वीकार' / 'swikaar' बोलें स्वीकार के लिए, 'मना' / 'mana' अस्वीकार के लिए, या 'दिखाओ' / 'dikhao' फोटो के लिए।",
        "no_pending": "कोई नया ऑर्डर नहीं है।",
        "no_production": "कोई उत्पादन में ऑर्डर नहीं है।",
        "order_accepted": "✅ {oid} स्वीकार किया गया!",
        "order_declined": "❌ {oid} अस्वीकार किया गया। थोक आउटलेट में भेजा गया।",
        "photo_sent_buyer": "📸 #{oid} का फोटो खरीदार को भेजा गया।",
        "pieces_label": "अनोखे हाथ से बुने टुकड़े थोक मूल्य पर — शिप करने के लिए तैयार।",
        "piece_label": "अनोखा हाथ से बुना टुकड़ा थोक मूल्य पर — शिप करने के लिए तैयार।",
        "woven_by": "बुनकर",
        "reason_label": "कारण:",
        "original_price": "मूल मूल्य",
    }
}

def get_ui_string(key: str, lang: str = "en") -> str:
    lang = lang if lang in UI_STRINGS else "en"
    return UI_STRINGS[lang].get(key, UI_STRINGS["en"].get(key, key))


def _strip_html(text: str) -> str:
    """Remove all HTML tags from a string so it is safe to inject into HTML."""
    if not text:
        return ""
    clean = str(text)
    # Decode common HTML entities FIRST so they don't become active tags after stripping
    clean = clean.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&nbsp;", " ").replace("&middot;", "·")
    clean = re.sub(r"<[^>]+>", "", clean)
    return clean.strip()


def _detect_language(text: str) -> str:
    """Return 'hi' if text contains Devanagari, else 'en'."""
    if any('\u0900' <= c <= '\u097F' for c in text):
        return "hi"
    return "en"


# ---------------------------------------------------------------------------
# CSS (full, with fixes for mobile)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg-deep:        #FBF2F9;
    --bg-surface:     #ffffff;
    --bg-card:        #FDF5FB;
    --bg-card-2:      #F3D9ED;
    --accent:         #9F2089;
    --accent-hover:   #7A1A6B;
    --accent-glow:    rgba(159,32,137,0.25);
    --text-primary:   #353543;
    --text-muted:     #616173;
    --text-white:     #ffffff;
    --success:        #038D63;
    --warning:        #EE7212;
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
    background: rgba(159,32,137,0.06); border: 1px solid rgba(159,32,137,0.2);
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
    box-shadow: 0 0 0 2px rgba(159,32,137,0.2) !important;
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
.order-card.below-base { border-color: var(--warning); background: rgba(238,114,18,0.04); }
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
.state-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--text-white);
    background: var(--text-muted);
}
.state-badge.state-active { background: var(--warning); color: var(--text-white); }
.state-badge.state-done   { background: var(--success); color: var(--text-white); }
.state-badge.state-pending { background: var(--accent); color: var(--text-white); }
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

@st.cache_data(show_spinner=False)
def _load_swatch_images() -> dict:
    """Return a dict mapping weave_style -> image_url from fabric_swatches.json."""
    try:
        p = Path(__file__).parent / "fabric_swatches.json"
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        mapping = {}
        for sw in data.get("fabric_swatches", []):
            style = sw.get("weave_style", "")
            url   = sw.get("image_url", "")
            if style and url and style not in mapping:
                mapping[style] = url
        return mapping
    except Exception:
        return {}

def _enrich_swatch_images(swatches: list) -> list:
    """Attach image_url to each swatch dict if not already present, by weave_style lookup."""
    image_map = _load_swatch_images()
    for sw in swatches:
        if not sw.get("image_url"):
            style = sw.get("weave_style", "")
            sw["image_url"] = image_map.get(style, "")
    return swatches

@st.cache_data(show_spinner=False, ttl=3600)
def _fetch_image_bytes(url: str) -> Optional[bytes]:
    """Fetch image bytes from URL server-side so st.image() gets raw bytes.
    Cached per URL so each image is only downloaded once per hour."""
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200 and resp.content:
            return resp.content
    except Exception:
        pass
    return None

# ---------------------------------------------------------------------------
# Edge TTS & STT
# ---------------------------------------------------------------------------
_EDGE_TTS_VOICES = {
    "hi": "hi-IN-MadhurNeural",
    "en": "en-IN-PrabhatNeural",
}

def _tts_edge(text: str, lang: str = "hi") -> Optional[bytes]:
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

def _tts_bytes(text: str, lang: str = "hi") -> Optional[bytes]:
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

def _convert_audio_to_wav(audio_bytes: bytes) -> tuple:
    raw_tmp = None
    wav_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
            f.write(audio_bytes)
            raw_tmp = f.name
        try:
            from pydub import AudioSegment
            seg = AudioSegment.from_file(raw_tmp)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wf:
                wav_path = wf.name
            seg.export(wav_path, format="wav")
        except (ImportError, Exception):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wf:
                wf.write(audio_bytes)
                wav_path = wf.name
        return wav_path, None
    except Exception as e:
        return None, f"Audio conversion error: {e}"
    finally:
        if raw_tmp:
            try:
                os.unlink(raw_tmp)
            except OSError:
                pass

def _stt_google(audio_bytes: bytes) -> tuple:
    if len(audio_bytes) < 4_000:
        return None, "Recording too short — please speak clearly for at least 2 seconds."
    try:
        import speech_recognition as sr
    except ImportError:
        return None, "SpeechRecognition library not installed. Please type your request."

    wav_path, conv_err = _convert_audio_to_wav(audio_bytes)
    if not wav_path:
        return None, conv_err or "Audio conversion failed."

    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 0.8
    try:
        with sr.AudioFile(wav_path) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.record(source)

        for lang_code in ("hi-IN", "en-IN"):
            try:
                text = recognizer.recognize_google(audio, language=lang_code)
                if text and len(text.strip()) > 1:
                    return text.strip(), None
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                return None, f"Speech recognition service unavailable: {e}"

        return None, "Could not understand. Please speak clearly in Hindi or English."
    except Exception as e:
        return None, f"Speech recognition error: {e}"
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass

def _transcribe_audio(audio_file) -> Tuple[Optional[str], Optional[str]]:
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
    return t in {"1", "2", "3", "one", "two", "three", "first", "second", "third",
                 "ek", "do", "teen", "pehla", "doosra", "teesra"}

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
        if k not in st.session_state:
            st.session_state[k] = v

def _init_weaver_state() -> None:
    if "weaver_orders" not in st.session_state:
        st.session_state["weaver_orders"] = _make_demo_orders()
    if "weaver_id" not in st.session_state:
        st.session_state["weaver_id"] = "W001"
    if "min_base_price" not in st.session_state:
        st.session_state["min_base_price"] = 1000
    if "audio_work_mode" not in st.session_state:
        st.session_state["audio_work_mode"] = False
    if "last_weaver_audio_hash" not in st.session_state:
        st.session_state["last_weaver_audio_hash"] = None
    if "custom_weavers" not in st.session_state:
        st.session_state["custom_weavers"] = []

def _make_demo_orders() -> list:
    return [
        {
            "order_id": "PKS-2847", "fabric": "Cotton-Silk", "weave_style": "Pochampally Ikat",
            "color": "Teal with gold border", "occasion": "Summer Wedding",
            "buyer_feel": "flowy, breathable yet elegant",
            "price": 1800, "delivery_by": "July 26, 2026", "status": "pending", "photo": None,
            "buyer_note": "Light saree, summer wedding, Rs.1500 - agent proposed Cotton-Silk",
            "weaver_location": "Pochampally",
        },
        {
            "order_id": "PKS-2831", "fabric": "Cotton", "weave_style": "Pochampally Ikat",
            "color": "Navy blue", "occasion": "Office / Daily Wear", "buyer_feel": "breathable, cool",
            "price": 750, "delivery_by": "July 20, 2026", "status": "accepted", "photo": None,
            "buyer_note": "Office wear, breathable cotton under Rs.800",
            "weaver_location": "Pochampally",
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
        f'100% ARTISAN DIRECT<br><span style="color:#038D63;">CASH ON DELIVERY AVAILABLE</span>'
        f'</div></div>', unsafe_allow_html=True,
    )

_STATE_STEPS = {
    "en": [
        ("greeting", "Start"), ("collecting", "Describe Intent"), ("retrieved", "Select Swatch"),
        ("fallback_pending", "Fallback"), ("swatch_selected", "Lock Fabric"),
        ("broadcasting", "Broadcast"), ("weaver_selected", "Matched"), ("confirmed", "Order Placed"),
    ],
    "hi": [
        ("greeting", "शुरू"), ("collecting", "इरादा बताएं"), ("retrieved", "स्वैच चुनें"),
        ("fallback_pending", "फॉलबैक"), ("swatch_selected", "फैब्रिक लॉक करें"),
        ("broadcasting", "प्रसारण"), ("weaver_selected", "मेल"), ("confirmed", "ऑर्डर कन्फर्म"),
    ],
}
_HIDDEN_STATES = {"fallback_pending", "broadcasting", "weaver_selected"}

def _step_indicator(current: str) -> None:
    lang = st.session_state.get("language", "en")
    steps = _STATE_STEPS.get(lang, _STATE_STEPS["en"])
    active = next((i for i, (k, _) in enumerate(steps) if k == current), 0)
    parts = ['<div style="display:flex;gap:1.2rem;align-items:center;margin-bottom:1rem;flex-wrap:wrap;">']
    for i, (key, label) in enumerate(steps):
        if key in _HIDDEN_STATES:
            continue
        cls = "done" if i < active else ("active" if i == active else "pending")
        color = "#038D63" if cls == "done" else ("var(--accent)" if cls == "active" else "var(--text-muted)")
        parts.append(
            f'<div class="step-row"><div class="step-dot {cls}"></div>'
            f'<span style="font-size:0.80rem;color:{color};font-weight:600;">{label}</span></div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Swatch card — fully bilingual, HTML-safe
# ---------------------------------------------------------------------------
def _swatch_card(swatch: dict, index: int) -> None:
    lang = st.session_state.get("language", "en")

    # ── SAFE field extraction: strip any HTML the agent may have included ──
    weave_style  = _strip_html(swatch.get("weave_style", "—"))
    color        = _strip_html(swatch.get("color", "—"))
    description  = _strip_html(swatch.get("description", ""))
    weaver_name  = _strip_html(swatch.get("weaver_name", "—"))
    weaver_state = _strip_html(swatch.get("weaver_state", ""))
    weaver_cluster = _strip_html(swatch.get("weaver_cluster", ""))
    price_inr    = swatch.get("price_inr", "?")
    delivery_days = swatch.get("delivery_days", "?")
    weaver_rating = swatch.get("weaver_rating", "?")

    location = weaver_state
    if weaver_cluster:
        location = f"{weaver_cluster}, {weaver_state}"

    # Escape for safe HTML injection
    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    tags_html = "".join(
        f'<span class="tag">{esc(_strip_html(t))}</span>'
        for t in swatch.get("sensory_tags", [])[:3]
    )

    # Bilingual label lookups
    lbl_authentic      = get_ui_string("common_authentic", lang)
    lbl_labor          = get_ui_string("swatch_labor", lang)
    lbl_placeholder    = get_ui_string("swatch_placeholder", lang)
    lbl_master_artisan = get_ui_string("common_master_artisan", lang)
    lbl_rating         = get_ui_string("common_rating", lang)
    lbl_delivery       = get_ui_string("common_delivery", lang)

    border_color = "var(--accent)" if index == 0 else "var(--border-strong)"
    image_url = swatch.get("image_url", "")

    # ── Embed image as base64 so the entire card renders in one st.markdown call ──
    # Streamlit strips external URLs from <img> tags even with unsafe_allow_html,
    # but a data URI is treated as inline content and always renders correctly.
    img_bytes = _fetch_image_bytes(image_url) if image_url else None
    if img_bytes:
        try:
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            # Detect mime type from magic bytes (JPEG vs PNG vs WebP)
            if img_bytes[:2] == b'\xff\xd8':
                mime = "image/jpeg"
            elif img_bytes[:8] == b'\x89PNG\r\n\x1a\n':
                mime = "image/png"
            elif img_bytes[:4] == b'RIFF' and img_bytes[8:12] == b'WEBP':
                mime = "image/webp"
            else:
                mime = "image/jpeg"
            img_tag = (
                f'<img src="data:{mime};base64,{img_b64}" '
                f'style="width:100%;border-radius:8px;display:block;margin-bottom:10px;" '
                f'alt="{esc(weave_style)}" loading="lazy">'
            )
        except Exception:
            img_tag = (
                f'<div style="background:rgba(159,32,137,0.08);border:1px dashed rgba(159,32,137,0.3);'
                f'border-radius:8px;padding:12px;font-size:0.78rem;color:var(--text-muted);'
                f'text-align:center;margin-bottom:10px;">{lbl_placeholder}</div>'
            )
    else:
        img_tag = (
            f'<div style="background:rgba(159,32,137,0.08);border:1px dashed rgba(159,32,137,0.3);'
            f'border-radius:8px;padding:12px;font-size:0.78rem;color:var(--text-muted);'
            f'text-align:center;margin-bottom:10px;">{lbl_placeholder}</div>'
        )

    st.markdown(f"""
    <div class="swatch-card" style="border:1.5px solid {border_color};">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="background:var(--bg-card);color:var(--text-primary);padding:2px 8px;
                border-radius:6px;font-size:0.75rem;font-weight:700;">{lbl_authentic}</span>
        </div>
        {img_tag}
        <div style="font-weight:800;font-size:1.05rem;color:var(--text-primary);
            margin-bottom:2px;">{esc(weave_style)}</div>
        <div style="font-size:0.85rem;color:var(--text-muted);margin-bottom:6px;">
            {esc(color)} · <span style="color:var(--accent);font-weight:600;">{esc(location)}</span>
        </div>
        <div class="swatch-price">₹{esc(str(price_inr))}</div>
        <div style="font-size:0.72rem;color:var(--text-muted);margin-bottom:6px;">{lbl_labor}</div>
        <div style="font-size:0.80rem;color:var(--text-primary);line-height:1.55;
            margin-bottom:6px;opacity:0.9;">{esc(description)}</div>
        <div style="margin:6px 0;">{tags_html}</div>
        <div class="divider"></div>
        <div class="swatch-label">{lbl_master_artisan}</div>
        <div class="swatch-value">{esc(weaver_name)}</div>
        <div style="font-size:0.80rem;color:var(--text-muted);">{esc(location)}</div>
        <div style="margin-top:4px;font-size:0.82rem;color:var(--text-primary);font-weight:600;">
            ⭐ {lbl_rating}: {esc(str(weaver_rating))} &nbsp;·&nbsp; {lbl_delivery}: {esc(str(delivery_days))} {'दिन' if lang == 'hi' else 'days'}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Core send function
# ---------------------------------------------------------------------------
def _send(user_text: str, *, force_new_search: bool = False) -> None:
    user_text = (user_text or "").strip()
    if not user_text:
        return

    # ── Detect language EARLY so the panel refreshes immediately ──
    detected = _detect_language(user_text)
    st.session_state["language"] = detected

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
    if (st.session_state["history"]
            and st.session_state["history"][-1][0] == "user"
            and st.session_state["history"][-1][1] == user_text):
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
    state = response.get("state", "greeting") if isinstance(response, dict) else "greeting"
    data  = response.get("data", {}) if isinstance(response, dict) else {}

    st.session_state["current_state"] = state
    st.session_state["history"].append(("agent", msg))
    st.session_state["agent_data"] = data

    # Replace swatches on every retrieval (never append stale ones)
    if data.get("swatches"):
        st.session_state["swatches"] = _enrich_swatch_images(data["swatches"])
    if data.get("order"):
        st.session_state["order"] = data["order"]

    if state == "confirmed" and data.get("order"):
        raw = data["order"]
        sw  = raw.get("selected_swatch") or {}
        wv  = raw.get("selected_weaver") or {}
        entry = {
            "order_id":    raw.get("order_id", "PKS-???"),
            "weave_style": sw.get("weave_style", "—"),
            "color":       sw.get("color", "—"),
            "price":       sw.get("price_inr", 0),
            "weaver_name": wv.get("weaver_name", "—"),
            "status":      "In Production",
            "photo_path":  None,
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

    # ---------------------------------------------------------------------------
    # FIX: Clear user input on next run if flag is set
    # ---------------------------------------------------------------------------
    if st.session_state.get("clear_user_input", False):
        st.session_state["user_input"] = ""
        st.session_state["clear_user_input"] = False

    st.markdown(f'<div class="trust-banner">{get_ui_string("trust_banner", lang)}</div>', unsafe_allow_html=True)

    if st.session_state.get("agent_thinking"):
        st.markdown(f'<div style="background:rgba(159,32,137,0.12);border-left:4px solid var(--accent);padding:0.8rem 1rem;border-radius:0 8px 8px 0;font-size:0.90rem;font-weight:600;color:var(--text-primary);margin-bottom:0.8rem;">{get_ui_string("agent_thinking", lang)}</div>', unsafe_allow_html=True)

    buyer_orders = st.session_state.get("buyer_orders", [])
    if buyer_orders:
        with st.expander(f"{get_ui_string('section_orders', lang)} ({len(buyer_orders)})", expanded=True):
            # Iterate over a snapshot to allow safe mutation
            for bo in list(buyer_orders):
                status = bo.get("status", "In Production")
                color = {
                    "In Production": "var(--warning)",
                    "Awaiting Approval": "var(--accent)",
                    "Completed": "#038D63",
                    "Photo Sent — Awaiting Approval": "var(--accent)",
                }.get(status, "var(--text-muted)")
                needs_approval = status in ("Awaiting Approval", "Photo Sent — Awaiting Approval")

                if status == "In Production":
                    status_label = get_ui_string("order_status_production", lang)
                elif status == "Awaiting Approval":
                    status_label = get_ui_string("order_status_approval", lang)
                elif status == "Completed":
                    status_label = get_ui_string("order_status_completed", lang)
                elif status == "Photo Sent — Awaiting Approval":
                    status_label = get_ui_string("order_status_photo_sent", lang)
                else:
                    status_label = status

                st.markdown(f"""
                <div style="background:var(--bg-surface);border:1px solid var(--border-strong);border-radius:10px;padding:1rem;margin-bottom:0.5rem;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;">
                        <div>
                            <div style="font-weight:800;font-size:1rem;color:var(--text-primary);">{bo["weave_style"]} · {bo["color"]}</div>
                            <div style="font-size:0.80rem;color:var(--text-muted);">#{bo["order_id"]} · Artisan: {bo["weaver_name"]} · ₹{int(bo["price"]):,}</div>
                        </div>
                        <div style="background:rgba(0,0,0,0.05);padding:4px 12px;border-radius:999px;font-size:0.75rem;font-weight:700;color:{color};">{status_label}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Show uploaded photo bytes if present, otherwise show placeholder
                photo_bytes = bo.get("photo_bytes")
                if photo_bytes and isinstance(photo_bytes, (bytes, bytearray)):
                    st.image(photo_bytes, caption=f"Progress photo — #{bo['order_id']}", width=280)
                elif bo.get("photo_path"):
                    # photo_path is a filename (no bytes stored) — show placeholder
                    st.markdown(
                        '<div style="background:rgba(159,32,137,0.08);border:1px dashed rgba(159,32,137,0.3);'
                        'border-radius:8px;padding:10px;font-size:0.78rem;color:var(--text-muted);'
                        'text-align:center;margin:6px 0;">📸 Fabric photo received — preview not available in demo mode</div>',
                        unsafe_allow_html=True,
                    )

                if needs_approval:
                    st.markdown(f"""
                    <div style="background:rgba(159,32,137,0.08);border:2px solid var(--accent);border-radius:12px;padding:1rem;margin:0.6rem 0;">
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
                            # Safe removal by order_id, not object reference
                            st.session_state["buyer_orders"] = [
                                o for o in st.session_state["buyer_orders"]
                                if o["order_id"] != bo["order_id"]
                            ]
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
                        # Safe removal by order_id
                        st.session_state["buyer_orders"] = [
                            o for o in st.session_state["buyer_orders"]
                            if o["order_id"] != bo["order_id"]
                        ]
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
                    # -----------------------------------------------------------------------
                    # FIX: set a flag to clear the input on the next run (instead of assigning now)
                    # -----------------------------------------------------------------------
                    st.session_state["clear_user_input"] = True
                    st.rerun()
                    return

# ---------------------------------------------------------------------------
# WEAVER PAGE
# ---------------------------------------------------------------------------
def _weaver_page() -> None:
    _init_weaver_state()
    all_weavers = _get_all_weavers()
    lang = st.session_state.get("language", "en")

    st.markdown(
        f'<div class="section-label">{get_ui_string("weaver_dashboard_title", lang)}</div>',
        unsafe_allow_html=True,
    )

    col_sel, col_stat = st.columns([2, 3])
    with col_sel:
        opts = [f"{w['id']} — {w.get('name','Unknown')} ({w.get('cluster','')})" for w in all_weavers]
        if not opts:
            opts = ["No weavers registered. Please onboard."]
        selected = st.selectbox(
            "Logged in as (प्रोफाइल)" if lang == "hi" else "Logged in as",
            opts,
            key="weaver_select",
        )
        if selected and " — " in selected:
            st.session_state["weaver_id"] = selected.split(" — ")[0]
        else:
            st.session_state["weaver_id"] = None

    current_id = st.session_state.get("weaver_id")
    profile = next((w for w in all_weavers if w.get("id") == current_id), {})
    if not profile:
        st.warning("Please select a valid weaver profile or register as a new weaver." if lang == "en"
                   else "कृपया एक वैध बुनकर प्रोफ़ाइल चुनें या नए बुनकर के रूप में पंजीकरण करें।")
        return

    with col_stat:
        fabric_list = profile.get("fabric_specialty", [])
        fabric_str  = ", ".join(fabric_list) if isinstance(fabric_list, list) else str(fabric_list)
        price_range = profile.get("price_range_inr", {})
        price_str   = (
            f"₹{int(price_range.get('min', 0)):,} – ₹{int(price_range.get('max', 0)):,}"
            if price_range else "—"
        )
        speciality_label = "विशेषता" if lang == "hi" else "Speciality"
        price_label      = "मूल्य सीमा" if lang == "hi" else "Price range"
        st.markdown(f"""
        <div style="background:var(--bg-surface);border:1px solid var(--border-strong);
            border-radius:10px;padding:0.75rem 1rem;font-size:0.82rem;line-height:1.7;">
            <span style="font-weight:700;color:var(--text-primary);">{profile.get("name","—")}</span>
            &nbsp;·&nbsp;
            <span style="color:var(--accent);font-weight:600;">{profile.get("cluster","—")}, {profile.get("state","—")}</span><br>
            <span style="color:var(--text-muted);">{speciality_label}: {profile.get("weave_style","—")} · {fabric_str}</span><br>
            <span style="color:var(--text-muted);">{price_label}: {price_str}</span>
            &nbsp;·&nbsp;
            <span style="color:var(--text-muted);">⭐ {profile.get("rating","—")}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    c_base, c_audio = st.columns([2, 2], gap="large")
    with c_base:
        st.markdown(f"**{get_ui_string('weaver_min_base', lang)}**")
        st.session_state["min_base_price"] = st.number_input(
            "Min Base Price (₹)", min_value=500, max_value=15000, step=100,
            value=st.session_state["min_base_price"], label_visibility="collapsed",
        )
    with c_audio:
        st.markdown(f"**{get_ui_string('weaver_audio_mode', lang)}**")
        toggle_label = "हिंदी घोषणाएँ चालू करें" if lang == "hi" else "Enable Hindi Announcements"
        st.session_state["audio_work_mode"] = st.toggle(toggle_label, value=st.session_state["audio_work_mode"])

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-label">{get_ui_string("weaver_voice_controls", lang)}</div>',
        unsafe_allow_html=True,
    )
    st.caption(get_ui_string("weaver_voice_caption", lang))

    # ── Voice command token lists ──
    ACCEPT_TOKENS = [
        "स्वीकार", "स्वीकृत", "मंजूर", "हाँ", "हां", "ठीक",
        "swikaar", "sweekar", "swikar", "sweekaro", "sweekaar karo",
        "manzoor", "manjoor", "theek hai", "theek", "sahi", "haan", "han",
        "accept", "yes", "ok", "okay", "done", "confirm", "approve",
    ]
    DECLINE_TOKENS = [
        "मना", "माना", "मना करो", "माना करो", "मना कर", "माना कर",
        "नहीं", "नही", "अस्वीकार", "रद्द",
        "mana kar", "mana karo", "maana kar", "maana karo",
        "nahi", "nahin",
        "decline", "reject", "cancel",
    ]
    SHOW_TOKENS = [
        "दिखाओ", "भेजो", "फोटो", "तस्वीर",
        "dikhao", "bhejo", "photo", "tasveer", "buyer ko dikhao",
        "send photo", "show buyer", "send to buyer",
    ]

    def _token_match(transcript, tokens):
        t = transcript.lower()
        for tok in tokens:
            tok = tok.lower()
            if len(tok) <= 3:
                if f" {tok} " in f" {t} ":
                    return True
            else:
                if tok in t:
                    return True
        return False

    def _live_pending():
        return [o for o in st.session_state.get("weaver_orders", []) if o.get("status") == "pending"]

    def _live_accepted():
        return [o for o in st.session_state.get("weaver_orders", []) if o.get("status") == "accepted"]

    w_audio = st.audio_input(
        "वॉइस कमांड रिकॉर्ड करें" if lang == "hi" else "Record Voice Command",
        label_visibility="collapsed",
        key="pakshi_weaver_audio",
    )

    if w_audio is not None:
        _w_hash = hash(bytes(w_audio.getbuffer()))
        if st.session_state.get("last_weaver_audio_hash") != _w_hash:
            st.session_state["last_weaver_audio_hash"] = _w_hash
            spinner_msg = "सुन रहे हैं..." if lang == "hi" else "Listening..."
            with st.spinner(spinner_msg):
                try:
                    text, err = _transcribe_audio(w_audio)
                except Exception as e:
                    text, err = None, f"Transcription error: {e}"

            if err:
                st.warning(f"{'ट्रांसक्रिप्शन विफल' if lang=='hi' else 'Transcription failed'}: {err}")
                st.caption(get_ui_string("tip_audio", lang))
                st.session_state["last_weaver_audio_hash"] = None
            else:
                heard_label = get_ui_string("heard", lang)
                st.info(f"{heard_label}: \"{text}\"")
                text_lower = text.lower().strip()
                action = None

                if _token_match(text_lower, ACCEPT_TOKENS):
                    action = "accept"
                elif _token_match(text_lower, DECLINE_TOKENS):
                    action = "decline"
                elif _token_match(text_lower, SHOW_TOKENS):
                    action = "show_buyer"
                else:
                    st.warning(get_ui_string("cmd_not_recognised", lang).format(text=text))

                if action is not None:
                    source_list  = _live_accepted() if action == "show_buyer" else _live_pending()
                    no_order_key = "no_production" if action == "show_buyer" else "no_pending"

                    if not source_list:
                        st.warning(get_ui_string(no_order_key, lang))
                        try:
                            msg_hi = ("Koi in-production order nahi hai."
                                      if action == "show_buyer"
                                      else "Aapke paas koi naya order nahi hai.")
                            if ab := _tts_bytes(msg_hi, lang="hi"):
                                _autoplay_audio(ab)
                        except Exception:
                            pass
                    else:
                        target_order = None
                        id_match = re.search(r'\b(\d{4})\b', text_lower)
                        if id_match:
                            spoken_id = id_match.group(1)
                            target_order = next(
                                (o for o in source_list if spoken_id in o.get("order_id", "")), None
                            )
                        if target_order is None:
                            ordinals = {
                                "first": 0, "pehla": 0, "ek": 0, "one": 0,
                                "second": 1, "doosra": 1, "do": 1, "two": 1,
                                "third": 2, "teesra": 2, "teen": 2, "three": 2,
                            }
                            for word, idx in ordinals.items():
                                if word in text_lower and idx < len(source_list):
                                    target_order = source_list[idx]
                                    break
                        if target_order is None:
                            target_order = source_list[0]

                        oid        = target_order["order_id"]
                        live_orders = st.session_state["weaver_orders"]
                        idx = next((i for i, o in enumerate(live_orders) if o["order_id"] == oid), None)

                        if idx is None:
                            st.error("Order not found. Please refresh." if lang == "en"
                                     else "ऑर्डर नहीं मिला। कृपया रिफ्रेश करें।")
                            st.rerun()
                            return

                        if action == "accept":
                            live_orders[idx]["status"] = "accepted"
                            for bo in st.session_state.get("buyer_orders", []):
                                if bo["order_id"] == oid:
                                    bo["status"] = "In Production"
                            st.session_state["weaver_orders"] = live_orders
                            st.success(get_ui_string("order_accepted", lang).format(oid=oid))
                            try:
                                if ab := _tts_bytes(f"Order {oid[-4:]} swikaar ho gaya.", lang="hi"):
                                    _autoplay_audio(ab)
                            except Exception:
                                pass
                            st.rerun()
                            return

                        elif action == "decline":
                            live_orders[idx]["status"] = "declined"
                            st.session_state["weaver_orders"] = live_orders
                            declined_bo = next(
                                (bo for bo in st.session_state.get("buyer_orders", [])
                                 if bo["order_id"] == oid), None
                            )
                            if declined_bo:
                                st.session_state.setdefault("one_of_a_kind", []).append({
                                    "order_id":       declined_bo["order_id"],
                                    "weave_style":    declined_bo.get("weave_style", "—"),
                                    "color":          declined_bo.get("color", "—"),
                                    "original_price": declined_bo.get("price", 0),
                                    "resale_price":   int(declined_bo.get("price", 0) * 0.65),
                                    "weaver_name":    declined_bo.get("weaver_name", "—"),
                                    "reason":         "Weaver declined the order",
                                })
                                st.session_state["buyer_orders"] = [
                                    bo for bo in st.session_state.get("buyer_orders", [])
                                    if bo["order_id"] != oid
                                ]
                            st.warning(get_ui_string("order_declined", lang).format(oid=oid))
                            try:
                                if ab := _tts_bytes(f"Order {oid[-4:]} mana kar diya.", lang="hi"):
                                    _autoplay_audio(ab)
                            except Exception:
                                pass
                            st.rerun()
                            return

                        elif action == "show_buyer":
                            live_orders[idx]["status"] = "awaiting_approval"
                            for bo in st.session_state.get("buyer_orders", []):
                                if bo["order_id"] == oid:
                                    bo["status"] = "Awaiting Approval"
                                    bo["photo_path"] = "voice_triggered_photo.jpg"
                            st.session_state["weaver_orders"] = live_orders
                            st.success(get_ui_string("photo_sent_buyer", lang).format(oid=oid))
                            try:
                                if ab := _tts_bytes(f"Order {oid[-4:]} buyer ko bhej diya.", lang="hi"):
                                    _autoplay_audio(ab)
                            except Exception:
                                pass
                            st.rerun()
                            return

    # ── Read orders aloud ──
    pending  = _live_pending()
    accepted = _live_accepted()

    if st.session_state.get("audio_work_mode") and (pending or accepted):
        read_btn_label = get_ui_string("weaver_read_orders", lang)
        if st.button(read_btn_label, use_container_width=False, key="read_orders_btn"):
            lines = []
            if pending:
                lines.append(f"Aapke paas {len(pending)} naye order hain.")
                for o in pending[:3]:
                    lines.append(
                        f"Order {o.get('order_id','')[-4:]}: "
                        f"{o.get('weave_style','fabric')}, keemat {o.get('price',0)} rupaye."
                    )
            if accepted:
                lines.append(f"{len(accepted)} order loom par chal rahe hain.")
            full_text = " ".join(lines)
            try:
                if ab := _tts_bytes(full_text, lang="hi"):
                    _autoplay_audio(ab, label="Your orders summary")
            except Exception as e:
                st.warning(f"TTS error: {e}")

    # ── Pending orders ──
    if pending:
        st.markdown(
            f'<div class="section-label" style="margin-top:1rem;">{get_ui_string("weaver_pending", lang)}</div>',
            unsafe_allow_html=True,
        )
        for order in pending:
            oid         = order["order_id"]
            order_price = int(order.get("price", 0))
            is_below    = order_price < st.session_state["min_base_price"]
            badge = (
                f'<span class="tag-warning">{get_ui_string("below_base", lang)} (₹{st.session_state["min_base_price"]})</span>'
                if is_below else
                f'<span class="tag">{get_ui_string("meets_base", lang)}</span>'
            )
            deliver_label = get_ui_string("deliver_by", lang)
            st.markdown(f"""
            <div class="order-card {'below-base' if is_below else ''}">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.4rem;">
                    <div>
                        <div style="font-weight:800;font-size:1.05rem;color:var(--text-primary);">{order.get("weave_style","—")}</div>
                        <div style="font-size:0.80rem;color:var(--text-muted);">#{oid}</div>
                        <div style="margin-top:4px;">{badge}</div>
                        <div style="font-size:0.80rem;color:var(--text-muted);margin-top:2px;">{order.get("color","—")} · {order.get("occasion","—")}</div>
                        <div style="font-size:0.78rem;color:var(--text-muted);">{deliver_label}: {order.get("delivery_by","—")}</div>
                    </div>
                    <div class="swatch-price">₹{order_price:,}</div>
                </div>
            </div>""", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            if b1.button(get_ui_string("weaver_accept", lang), key=f"acc_{oid}", use_container_width=True):
                live_orders = st.session_state["weaver_orders"]
                idx = next((i for i, o in enumerate(live_orders) if o["order_id"] == oid), None)
                if idx is not None:
                    live_orders[idx]["status"] = "accepted"
                    for bo in st.session_state.get("buyer_orders", []):
                        if bo["order_id"] == oid:
                            bo["status"] = "In Production"
                    st.session_state["weaver_orders"] = live_orders
                try:
                    if ab := _tts_bytes("Order swikaar kiya", lang="hi"):
                        _autoplay_audio(ab)
                except Exception:
                    pass
                st.rerun()
                return

            if b2.button(get_ui_string("weaver_decline", lang), key=f"dec_{oid}", use_container_width=True):
                live_orders = st.session_state["weaver_orders"]
                idx = next((i for i, o in enumerate(live_orders) if o["order_id"] == oid), None)
                if idx is not None:
                    live_orders[idx]["status"] = "declined"
                    st.session_state["weaver_orders"] = live_orders
                declined_bo = next(
                    (bo for bo in st.session_state.get("buyer_orders", []) if bo["order_id"] == oid), None
                )
                if declined_bo:
                    st.session_state.setdefault("one_of_a_kind", []).append({
                        "order_id":       declined_bo["order_id"],
                        "weave_style":    declined_bo.get("weave_style", "—"),
                        "color":          declined_bo.get("color", "—"),
                        "original_price": declined_bo.get("price", 0),
                        "resale_price":   int(declined_bo.get("price", 0) * 0.65),
                        "weaver_name":    declined_bo.get("weaver_name", "—"),
                        "reason":         "Weaver declined the order",
                    })
                    st.session_state["buyer_orders"] = [
                        bo for bo in st.session_state.get("buyer_orders", [])
                        if bo["order_id"] != oid
                    ]
                st.rerun()
                return

    # ── Accepted / in-production ──
    if accepted:
        st.markdown(
            f'<div class="section-label" style="margin-top:1rem;">{get_ui_string("weaver_production", lang)}</div>',
            unsafe_allow_html=True,
        )
        for order in accepted:
            oid = order["order_id"]
            production_label = get_ui_string("order_status_production", lang)
            st.markdown(f"""
            <div class="order-card accepted">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div style="font-weight:700;font-size:0.95rem;color:var(--text-primary);">{order.get("weave_style","—")}</div>
                        <div style="font-size:0.80rem;color:var(--text-muted);">#{oid} · ₹{int(order.get("price", 0)):,}</div>
                    </div>
                    <div style="background:var(--warning);color:#fff;padding:4px 12px;border-radius:999px;
                        font-size:0.75rem;font-weight:700;">{production_label}</div>
                </div>
            </div>""", unsafe_allow_html=True)
            upload_label = get_ui_string("upload_photo", lang)
            uploaded = st.file_uploader(
                f"{upload_label} — #{oid}",
                type=["jpg", "jpeg", "png"],
                key=f"photo_{oid}",
                label_visibility="visible",
            )
            if uploaded:
                st.image(uploaded.getvalue(), caption=f"{'प्रगति फोटो' if lang=='hi' else 'Progress photo'} — {oid}", width=260)
            send_photo_label = f"{get_ui_string('weaver_send_photo', lang)} — #{oid}"
            if st.button(send_photo_label, key=f"show_{oid}"):
                photo_name         = uploaded.name if uploaded else "loom_snapshot.jpg"
                photo_bytes_stored = uploaded.getvalue() if uploaded else None
                live_orders = st.session_state["weaver_orders"]
                idx = next((i for i, o in enumerate(live_orders) if o["order_id"] == oid), None)
                if idx is not None:
                    live_orders[idx]["status"] = "awaiting_approval"
                    live_orders[idx]["photo"]  = photo_name
                    st.session_state["weaver_orders"] = live_orders
                for bo in st.session_state.get("buyer_orders", []):
                    if bo["order_id"] == oid:
                        bo["status"]     = "Awaiting Approval"
                        bo["photo_path"] = photo_name
                        if photo_bytes_stored:
                            bo["photo_bytes"] = photo_bytes_stored
                success_msg = get_ui_string("photo_sent_success", lang).format(oid=oid)
                st.success(success_msg)
                st.rerun()
                return

    # ── Awaiting approval ──
    awaiting = [o for o in st.session_state.get("weaver_orders", []) if o.get("status") == "awaiting_approval"]
    if awaiting:
        st.markdown(
            f'<div class="section-label" style="margin-top:1rem;">{get_ui_string("weaver_awaiting", lang)}</div>',
            unsafe_allow_html=True,
        )
        for order in awaiting:
            approval_msg = get_ui_string("awaiting_approval_msg", lang).format(oid=order["order_id"])
            st.info(approval_msg)

    st.markdown('<div style="height:1.2rem;"></div>', unsafe_allow_html=True)
    if st.button(get_ui_string("weaver_simulate", lang), use_container_width=True):
        specialty = profile.get("weave_style", "Handloom")
        weave_map = {
            "Ikat":       ("Pochampally Ikat", "Cotton-Silk"),
            "Banarasi":   ("Banarasi Brocade", "Silk"),
            "Block Print":("Block Print", "Cotton"),
            "Kanjivaram": ("Kanjivaram Silk", "Silk"),
            "Tussar":     ("Tussar", "Silk"),
            "Chanderi":   ("Chanderi", "Cotton-Silk"),
            "Paithani":   ("Paithani", "Silk"),
            "Patola":     ("Patola", "Silk"),
        }
        weave_style, fabric_type = "Handloom", "Cotton"
        for key, (w, f) in weave_map.items():
            if key.lower() in specialty.lower():
                weave_style, fabric_type = w, f
                break
        new_order = {
            "order_id":       f"PKS-{random.randint(2900, 2999)}",
            "fabric":         fabric_type,
            "weave_style":    weave_style,
            "color":          random.choice(["Maroon", "Teal", "Mustard Yellow", "Ivory", "Navy Blue", "Deep Red"]),
            "occasion":       random.choice(["Wedding", "Festival", "Casual", "Office"]),
            "buyer_feel":     random.choice(["royal, heavy", "light, airy", "elegant", "comfortable"]),
            "price":          random.choice([800, 1200, 1800, 2500, 3500, 5000]),
            "delivery_by":    "July 28, 2026",
            "status":         "pending",
            "photo":          None,
            "buyer_note":     f"Direct voice broadcast matching your {specialty} specialty.",
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
    st.markdown(
        f'<div class="section-label">{get_ui_string("ooak_title", lang)}</div>',
        unsafe_allow_html=True,
    )

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
            <div style="font-size:0.95rem;font-weight:700;margin-bottom:0.4rem;">
                {get_ui_string('ooak_empty', lang)}
            </div>
        </div>""", unsafe_allow_html=True)
        return

    count_label = (
        get_ui_string("pieces_label", lang) if len(items) > 1
        else get_ui_string("piece_label", lang)
    )
    st.caption(f"{len(items)} {count_label}")

    for idx, item in enumerate(items):
        orig   = item.get("original_price", 0)
        resale = item.get("resale_price", 0)
        discount = int((1 - resale / orig) * 100) if orig else 0

        tags_html = "".join(
            f'<span class="tag">{_strip_html(t)}</span>'
            for t in item.get("sensory_tags", [])[:3]
        )

        woven_by_label  = get_ui_string("woven_by", lang)
        reason_label    = get_ui_string("reason_label", lang)
        orig_price_label = get_ui_string("original_price", lang)
        ready_label     = get_ui_string("ooak_ready", lang)

        col_card, col_btn = st.columns([5, 1], gap="small")
        with col_card:
            st.markdown(f"""
            <div class="card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;">
                    <div>
                        <div style="font-weight:800;font-size:1.05rem;color:var(--text-primary);">
                            {_strip_html(item.get("weave_style","—"))} &middot; {_strip_html(item.get("color","—"))}
                        </div>
                        <div style="font-size:0.78rem;color:var(--text-muted);margin-top:2px;">
                            #{item.get("order_id","—")} &middot; {reason_label} {_strip_html(item.get("reason","Rejected custom piece"))}
                        </div>
                        <div style="font-size:0.78rem;color:var(--text-muted);margin-top:2px;">
                            {woven_by_label}: <strong style="color:var(--text-primary);">{_strip_html(item.get("weaver_name","—"))}</strong>
                            &middot; {_strip_html(item.get("weaver_cluster","—"))}, {_strip_html(item.get("weaver_state","—"))}
                        </div>
                        <div style="margin-top:6px;">{tags_html}
                            <span class="tag" style="background:rgba(3,141,99,0.15);color:#038D63;">{ready_label}</span>
                        </div>
                    </div>
                    <div style="text-align:right;flex-shrink:0;">
                        <div style="font-size:0.78rem;color:var(--text-muted);">{orig_price_label}: <span style="text-decoration:line-through;">₹{orig:,}</span></div>
                        <div class="swatch-price">₹{resale:,}</div>
                        <div style="background:rgba(3,141,99,0.2);color:#038D63;padding:2px 8px;
                            border-radius:999px;font-size:0.72rem;font-weight:700;
                            display:inline-block;margin-top:2px;">{discount}% off</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
        with col_btn:
            st.markdown('<div style="height:1.2rem;"></div>', unsafe_allow_html=True)
            buy_label = get_ui_string("btn_buy_now", lang)
            if st.button(buy_label, key=f"buy_{item.get('order_id',idx)}_{idx}", use_container_width=True):
                added_msg = get_ui_string("order_added", lang)
                st.success(f"#{item.get('order_id','')} {added_msg}")

# ---------------------------------------------------------------------------
# WEAVER ONBOARDING PAGE
# ---------------------------------------------------------------------------
def _onboarding_page() -> None:

    # ── GPS query param catch — runs FIRST before any widget renders ──
    _gps_place_param = st.query_params.get("gps_place")
    _gps_state_param = st.query_params.get("gps_state")
    if _gps_place_param:
        st.session_state["gps_place"] = _gps_place_param
        st.session_state["_cluster_field"] = _gps_place_param
        if _gps_state_param:
            st.session_state["gps_state"] = _gps_state_param
        try:
            del st.query_params["gps_place"]
            if "gps_state" in st.query_params:
                del st.query_params["gps_state"]
        except Exception:
            pass
        st.rerun()

    def _parse_onboarding_text(text: str) -> dict:
        KNOWN_CLUSTERS = [
            "pochampally", "venkatagiri", "kanchipuram", "ilkal", "kota", "chanderi",
            "maheshwar", "dharmavaram", "mysore", "sambalpuri", "bagru", "sanganer",
            "kutch", "kerala", "tamil nadu", "andhra pradesh", "telangana", "karnataka",
            "rajasthan", "west bengal", "odisha", "gujarat", "maharashtra", "bihar",
            "uttar pradesh", "varanasi", "banaras", "kashi", "paithani", "yeola",
            "molakalmuru", "uppada", "nuapatna", "arni", "balaramapuram", "coimbatore",
            "salem", "bishnupur", "murshidabad", "shantipur", "bhagalpur"
        ]
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
        t = text.lower().strip()
        t = re.sub(r'[.,;:!?]', ' ', t)
        t = re.sub(r'\s+', ' ', t)

        clean_digits = re.sub(r'\D', '', t)
        phone_match  = re.search(r'(\d{10})', clean_digits)
        if phone_match:
            result["phone"] = phone_match.group(1)

        for hindi, eng in weave_map.items():
            if hindi in t:
                result["specialty"] = eng.title()
                break
        if not result["specialty"]:
            for w in english_weaves:
                if w in t:
                    result["specialty"] = w.title()
                    break

        cluster_found = None
        for cluster in KNOWN_CLUSTERS:
            if cluster in t:
                cluster_found = cluster.title()
                break
        if cluster_found:
            result["cluster"] = cluster_found

        if not result["cluster"]:
            english_weaves_lower = [w.lower() for w in english_weaves]
            weave_values_lower   = [v.lower() for v in weave_map.values()]
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
            ]
            for pattern in village_patterns:
                match = re.search(pattern, t, re.IGNORECASE)
                if match:
                    candidate  = match.group(1).strip().lower()
                    cand_words = [w for w in candidate.split() if w not in exclusion_set and len(w) > 2]
                    if cand_words:
                        result["cluster"] = " ".join(cand_words).title()
                        break

        name_found = None
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

        if not name_found:
            name_text = t
            if result["phone"]:
                name_text = re.sub(r'\d', ' ', name_text)
            if result["cluster"]:
                name_text = name_text.replace(result["cluster"].lower(), " ")
            if result["specialty"]:
                spec_lower = result["specialty"].lower()
                name_text  = name_text.replace(spec_lower, " ")
                for hindi, eng in weave_map.items():
                    if eng.lower() == spec_lower:
                        name_text = name_text.replace(hindi, " ")
            sw_set = {
                "main","mera","my","name","naam","hai","is","hoon","hun",
                "है","मैं","हूँ","से","ki","की","में","ka","का","ke","के",
                "number","phone","hu","hain","ho","raha","rahi","banati","banata"
            }
            for sw in sw_set:
                name_text = re.sub(r'(?:^|\s)' + re.escape(sw) + r'(?:\s|$)', ' ', name_text, flags=re.IGNORECASE)
            name_text = re.sub(r'\s+', ' ', name_text).strip()
            if name_text:
                words = [w for w in name_text.split() if len(w) > 1]
                if words:
                    name_found = " ".join(words[:2]).title()

        result["name"] = name_found or ""

        if not result["name"]:
            words = t.split()
            sw_fb = {
                "main","mera","my","name","naam","hai","is","hoon","hun",
                "है","मैं","हूँ","से","ki","की","में","ka","का","ke","के",
                "number","phone","hu","hain","ho","raha","rahi","banati","banata"
            }
            for i, w in enumerate(words):
                w_clean = w.strip('.,;:!?')
                w_lower = w_clean.lower()
                if (w_lower not in sw_fb and not w_clean.isdigit() and len(w_clean) > 1
                        and not (result["cluster"] and w_lower in result["cluster"].lower())
                        and not (result["specialty"] and w_lower in result["specialty"].lower())):
                    cand = w_clean.title()
                    if i + 1 < len(words):
                        nw      = words[i+1].strip('.,;:!?')
                        nw_low  = nw.lower()
                        if (nw_low not in sw_fb and not nw.isdigit() and len(nw) > 1
                                and not (result["cluster"] and nw_low in result["cluster"].lower())
                                and not (result["specialty"] and nw_low in result["specialty"].lower())):
                            cand += " " + nw.title()
                    result["name"] = cand
                    break

        return result

    # ── end parser ──

    lang = st.session_state.get("language", "en")
    st.markdown(
        f'<div class="section-label">{get_ui_string("onboard_title", lang)}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"""
    <div style="background:rgba(238,114,18,0.08);border:1px solid rgba(238,114,18,0.25);
        border-radius:10px;padding:0.75rem 1rem;margin-bottom:1rem;font-size:0.82rem;
        color:var(--text-primary);line-height:1.6;">
        {get_ui_string("onboard_desc", lang)}
    </div>
    """, unsafe_allow_html=True)

    for key, default in [
        ("onboard_submitted", False), ("onboard_data", {}),
        ("reg_name", ""), ("reg_cluster", ""), ("reg_specialty", ""),
        ("reg_phone", ""), ("last_reg_audio_hash", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    if st.session_state["onboard_submitted"]:
        d = st.session_state["onboard_data"]
        cluster_lbl = get_ui_string("onboard_cluster", lang)
        fabric_lbl  = get_ui_string("onboard_fabric", lang)
        st.markdown(f"""
        <div style="background:rgba(3,141,99,0.08);border:1.5px solid #038D63;
            border-radius:12px;padding:1.4rem;text-align:center;margin-top:1rem;">
            <div style="font-size:1.3rem;font-weight:800;color:#038D63;margin-bottom:0.4rem;">
                {get_ui_string("onboard_submitted", lang)}
            </div>
            <div style="font-size:0.85rem;color:var(--text-primary);line-height:1.7;">
                <strong>{d.get("name","")}</strong> {'पंजीकृत हो गए।' if lang=='hi' else 'registered successfully.'}<br>
                {cluster_lbl}: {d.get("cluster","")} · {fabric_lbl}: {d.get("fabric","")}<br>
                <span style="color:var(--accent);font-weight:600;">
                {'पुष्टि' if lang=='hi' else 'Confirmation'} {d.get("phone","")} {'पर व्हाट्सएप के जरिए भेजी जाएगी।' if lang=='hi' else 'via WhatsApp.'}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        _oid = d.get("id", "") or st.session_state.get("weaver_id", "")
        if _oid:
            st.success(f"{'बुनकर आईडी' if lang=='hi' else 'Weaver ID'}: {_oid}")

        oc1, oc2 = st.columns(2)
        if oc1.button(get_ui_string("onboard_register_another", lang), use_container_width=True):
            st.session_state["onboard_submitted"] = False
            st.session_state["onboard_data"] = {}
            st.session_state.pop("gps_place", None)
            st.session_state.pop("gps_state", None)
            st.rerun()
        if oc2.button(get_ui_string("onboard_go_dashboard", lang), use_container_width=True):
            st.session_state["onboard_submitted"] = False
            st.session_state["onboard_data"] = {}
            st.query_params["tab"] = "Weaver Dashboard"
            st.rerun()
        return

    # GPS — iframe does geolocation + Nominatim fetch entirely client-side, then
    # postMessages village+state back to parent. Parent catches via st.query_params
    # written by a ?gps_place=...&gps_state=... redirect — one fast reload, no server geocode.
    gps_label  = get_ui_string("onboard_gps", lang)
    gps_wait   = "स्थान मिल रहा है..." if lang == "hi" else "Getting location..."
    gps_denied = ("अनुमति अस्वीकृत। ब्राउज़र में लोकेशन चालू करें।"
                  if lang == "hi"
                  else "Permission denied — allow location in browser.")
    # GPS: iframe gets location + geocodes client-side, then fills hidden st.text_inputs
    # by finding their DOM <input> elements and firing React synthetic change events.
    # This works on Streamlit Cloud where all window.top/parent navigation is CSP-blocked.
    gps_receiver = st.text_input("gps_place_hidden", key="gps_place_raw", label_visibility="collapsed")
    gps_state_receiver = st.text_input("gps_state_hidden", key="gps_state_raw", label_visibility="collapsed")

    if st.session_state.get("gps_place_raw") and st.session_state["gps_place_raw"] != st.session_state.get("gps_place_raw_prev", ""):
        st.session_state["gps_place"] = st.session_state["gps_place_raw"]
        st.session_state["_cluster_field"] = st.session_state["gps_place_raw"]
        st.session_state["gps_place_raw_prev"] = st.session_state["gps_place_raw"]
    if st.session_state.get("gps_state_raw") and st.session_state["gps_state_raw"] != st.session_state.get("gps_state_raw_prev", ""):
        st.session_state["gps_state"] = st.session_state["gps_state_raw"]
        st.session_state["gps_state_raw_prev"] = st.session_state["gps_state_raw"]

    st.iframe(f"""<!DOCTYPE html><html><body style="margin:0;padding:4px;background:transparent;">
    <button id="gb" onclick="doGPS()" style="background:#9F2089;color:#fff;border:none;
        border-radius:8px;padding:0.45rem 1.1rem;font-size:0.9rem;font-weight:700;cursor:pointer;">
        \U0001f4cd {gps_label}
    </button>
    <span id="gs" style="margin-left:0.7rem;font-size:0.8rem;color:#888;"></span>
    <script>
    const STATE_MAP = {{
        "andhra pradesh":"Andhra Pradesh","bihar":"Bihar","gujarat":"Gujarat",
        "jharkhand":"Jharkhand","karnataka":"Karnataka","kerala":"Kerala",
        "madhya pradesh":"Madhya Pradesh","maharashtra":"Maharashtra","odisha":"Odisha",
        "rajasthan":"Rajasthan","tamil nadu":"Tamil Nadu","telangana":"Telangana",
        "uttar pradesh":"Uttar Pradesh","west bengal":"West Bengal"
    }};
    function setStreamlitInput(labelText, value) {{
        // Find all input elements in parent document, match by aria-label or placeholder
        var inputs = window.parent.document.querySelectorAll('input[type="text"]');
        for (var i=0; i<inputs.length; i++) {{
            var inp = inputs[i];
            if (inp.getAttribute('aria-label') === labelText ||
                inp.closest('[data-testid="stTextInput"]') &&
                inp.closest('[data-testid="stTextInput"]').querySelector('label') &&
                inp.closest('[data-testid="stTextInput"]').querySelector('label').innerText.trim() === labelText) {{
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(inp, value);
                inp.dispatchEvent(new window.parent.Event('input', {{ bubbles: true }}));
                inp.dispatchEvent(new window.parent.Event('change', {{ bubbles: true }}));
                return true;
            }}
        }}
        return false;
    }}
    function doGPS() {{
        var btn=document.getElementById('gb'), s=document.getElementById('gs');
        if (!navigator.geolocation) {{ s.innerText='Not supported.'; return; }}
        btn.disabled=true; s.innerText='{gps_wait}';
        navigator.geolocation.getCurrentPosition(function(pos) {{
            var lat=pos.coords.latitude, lon=pos.coords.longitude;
            s.innerText='Fetching address...';
            fetch('https://nominatim.openstreetmap.org/reverse?lat='+lat+'&lon='+lon+'&format=json&zoom=14&addressdetails=1',
                {{headers:{{'User-Agent':'Pakshi-App'}}}})
            .then(r=>r.json()).then(function(d) {{
                var a=d.address||{{}};
                var village=a.village||a.hamlet||a.neighbourhood||a.suburb||a.town||a.city||(d.display_name||'').split(',')[0];
                village = village.trim();
                var rawState=(a.state||'').toLowerCase();
                var state=STATE_MAP[rawState]||'Other';
                s.innerText='\u2705 '+village+' · '+state;
                // Fill the hidden receiver inputs via React synthetic events
                setStreamlitInput('gps_place_hidden', village);
                setTimeout(function() {{ setStreamlitInput('gps_state_hidden', state); }}, 300);
            }}).catch(function(e) {{
                btn.disabled=false; s.innerText='Geocode error: '+e.message;
            }});
        }}, function(err) {{
            btn.disabled=false;
            s.innerText=err.code===1?'{gps_denied}':'Error: '+err.message;
        }}, {{enableHighAccuracy:true,timeout:8000,maximumAge:0}});
    }}
    </script></body></html>""", height=55)



    # Voice fill
    speak_hint_en = "Please say your name, village, weave style, and phone number."
    speak_hint_hi = "कृपया अपना नाम, गाँव, बुनाई शैली और फोन नंबर बोलें।"
    example_en = '"My name is Shruti, I am from Pochampally, I do Ikat, my number is 9876543210"'
    example_hi = '"मेरा नाम अनिका है, पोचमपल्ली से हूँ, इकट बनाती हूँ, 9876543210"'

    st.markdown(f"""
    <div style="background:rgba(159,32,137,0.07);border:2px solid rgba(159,32,137,0.35);
        border-radius:14px;padding:1rem 1.2rem;margin-bottom:1rem;">
        <div style="font-weight:700;font-size:1rem;color:var(--text-primary);margin-bottom:4px;">
            {get_ui_string('onboard_speak', lang)}
        </div>
        <div style="font-size:0.82rem;color:var(--text-muted);line-height:1.6;">
            <strong>{'English' if lang=='en' else 'हिंदी'}:</strong>
            {speak_hint_en if lang=='en' else speak_hint_hi}<br>
            <em>{example_en if lang=='en' else example_hi}</em>
        </div>
    </div>
    """, unsafe_allow_html=True)

    reg_audio = st.audio_input(
        "बोलकर फॉर्म भरें" if lang == "hi" else "Speak to fill the form",
        key="reg_audio", label_visibility="collapsed",
    )
    if reg_audio is not None:
        _audio_hash = hash(bytes(reg_audio.getbuffer()))
        if st.session_state.get("last_reg_audio_hash") != _audio_hash:
            st.session_state["last_reg_audio_hash"] = _audio_hash
            spinner_msg = "विवरण निकाला जा रहा है..." if lang == "hi" else "Listening and extracting details..."
            with st.spinner(spinner_msg):
                text, err = _transcribe_audio(reg_audio)
            if err:
                st.warning(f"{'ट्रांसक्रिप्शन विफल' if lang=='hi' else 'Could not transcribe'}: {err}")
            else:
                st.markdown(
                    f'<div style="background:rgba(3,141,99,0.08);border:1px solid #038D63;'
                    f'border-radius:8px;padding:0.6rem 1rem;font-size:0.85rem;margin-bottom:0.5rem;">'
                    f'{"सुना" if lang=="hi" else "Heard"}: <em>{text}</em></div>',
                    unsafe_allow_html=True,
                )
                parsed = _parse_onboarding_text(text)
                filled = [k for k, v in parsed.items() if v]
                for key, val in parsed.items():
                    if val:
                        st.session_state[f"reg_{key}"] = val
                if filled:
                    auto_msg = (f"स्वतः भरा गया: {', '.join(filled)}. नीचे जाँचें और सुधारें।"
                                if lang == "hi"
                                else f"Auto-filled: {', '.join(filled)}. Review and correct below.")
                    st.success(auto_msg)
                else:
                    no_extract = ("ऑडियो से विवरण नहीं निकाल सका। कृपया नीचे टाइप करें।"
                                  if lang == "hi"
                                  else "Could not extract details. Please type the fields manually.")
                    st.warning(no_extract)
            st.rerun()

    with st.form("onboard_form"):
        st.markdown(
            f'<div class="section-label">{get_ui_string("onboard_basic", lang)}</div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        default_cluster = st.session_state.get("gps_place", "") or st.session_state.get("reg_cluster", "")
        name    = c1.text_input(get_ui_string("onboard_name", lang),    value=st.session_state.get("reg_name", ""),    placeholder="e.g. Padmavathi Devi")
        phone   = c2.text_input(get_ui_string("onboard_phone", lang),   value=st.session_state.get("reg_phone", ""),   placeholder="10-digit number")
        c3, c4  = st.columns(2)
        cluster = c3.text_input(get_ui_string("onboard_cluster", lang), key="_cluster_field", placeholder="e.g. Pochampally")
        if not st.session_state.get("_cluster_field") and default_cluster:
            st.session_state["_cluster_field"] = default_cluster
        _state_options = [
            "Andhra Pradesh", "Bihar", "Gujarat", "Jharkhand", "Karnataka",
            "Kerala", "Madhya Pradesh", "Maharashtra", "Odisha", "Rajasthan",
            "Tamil Nadu", "Telangana", "Uttar Pradesh", "West Bengal", "Other"
        ]
        _gps_state = st.session_state.get("gps_state", "")
        _state_index = _state_options.index(_gps_state) if _gps_state in _state_options else 0
        state   = c4.selectbox(get_ui_string("onboard_state", lang), _state_options, index=_state_index)

        st.markdown(
            f'<div class="section-label" style="margin-top:0.8rem;">{get_ui_string("onboard_craft", lang)}</div>',
            unsafe_allow_html=True,
        )
        c5, c6  = st.columns(2)
        fabric  = c5.multiselect(get_ui_string("onboard_fabric", lang), ["Cotton", "Silk", "Cotton-Silk", "Tussar", "Linen"])
        weave   = c6.text_input(get_ui_string("onboard_weave", lang),   value=st.session_state.get("reg_specialty", ""), placeholder="e.g. Ikat, Jamdani, Block Print")
        c7, c8  = st.columns(2)
        min_p   = c7.number_input(get_ui_string("onboard_min_price", lang),   min_value=300, max_value=50000, value=1000, step=100)
        delivery = c8.number_input(get_ui_string("onboard_delivery", lang), min_value=3, max_value=60, value=14, step=1)

        st.markdown(
            f'<div class="section-label" style="margin-top:0.8rem;">{get_ui_string("onboard_verification", lang)}</div>',
            unsafe_allow_html=True,
        )
        c9, c10 = st.columns(2)
        aadhaar = c9.text_input(get_ui_string("onboard_aadhaar", lang), placeholder="XXXX", max_chars=4)
        bank    = c10.text_input(get_ui_string("onboard_bank", lang),   placeholder="Account number")

        whatsapp = st.checkbox(get_ui_string("onboard_whatsapp", lang))
        custom   = st.checkbox(get_ui_string("onboard_custom", lang))
        consent  = st.checkbox(get_ui_string("onboard_consent", lang))

        lang_pref = st.selectbox(get_ui_string("onboard_lang", lang), [
            "Hindi", "Telugu", "Tamil", "Kannada", "Bengali", "Gujarati", "Marathi", "English"
        ])

        photo = st.file_uploader(get_ui_string("onboard_photo", lang), type=["jpg","jpeg","png"])
        if photo:
            st.image(photo, caption="Sample work preview", width=260)

        submitted = st.form_submit_button(get_ui_string("onboard_submit", lang), use_container_width=True)

        if submitted:
            errors = []
            if not name.strip():
                errors.append("Name is required." if lang=="en" else "नाम आवश्यक है।")
            if not phone.strip() or len(phone.strip()) != 10 or not phone.strip().isdigit():
                errors.append("Valid 10-digit mobile number is required." if lang=="en" else "10-अंकीय मोबाइल नंबर आवश्यक है।")
            if not cluster.strip():
                errors.append("Village / Cluster is required." if lang=="en" else "गाँव / क्लस्टर आवश्यक है।")
            if not fabric:
                errors.append("Select at least one fabric speciality." if lang=="en" else "कम से कम एक फैब्रिक विशेषता चुनें।")
            if not consent:
                errors.append("You must agree to list on Meesho." if lang=="en" else "मीशो पर सूचीबद्ध होने के लिए सहमति आवश्यक है।")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                new_id = f"CW{random.randint(100,999)}"
                new_profile = {
                    "id": new_id, "name": name.strip(), "cluster": cluster.strip(),
                    "state": state, "fabric_specialty": fabric, "weave_style": weave.strip(),
                    "price_range_inr": {"min": min_p, "max": min_p * 3},
                    "rating": 4.0, "orders_completed": 0, "active": True,
                    "phone": phone.strip(), "whatsapp": whatsapp,
                    "accepts_custom": custom, "language": lang_pref,
                    "photo": photo.getvalue() if photo else None,
                }
                st.session_state.setdefault("custom_weavers", []).append(new_profile)
                st.session_state["weaver_id"] = new_id
                st.session_state["onboard_data"] = {
                    "id": new_id, "name": name.strip(), "phone": phone.strip(),
                    "cluster": cluster.strip(), "state": state,
                    "fabric": ", ".join(fabric), "weave": weave.strip(),
                    "min_price": min_p, "delivery_days": delivery,
                    "whatsapp": whatsapp, "accepts_custom": custom, "language": lang_pref,
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
        lang = st.session_state.get("language", "en")
        st.markdown(
            f'<div style="background:rgba(218,65,103,0.1);border:1px solid rgba(159,32,137,0.3);'
            f'border-radius:8px;padding:0.5rem 1rem;font-size:0.82rem;color:#D9A6D0;'
            f'margin-bottom:0.8rem;">{get_ui_string("warming_up", lang)}</div>',
            unsafe_allow_html=True,
        )
        st.session_state["app_loaded"] = True

    default_tab = 0
    tab_param   = st.query_params.get("tab")
    if tab_param:
        if "Buyer" in tab_param:            default_tab = 0
        elif "Weaver Dashboard" in tab_param: default_tab = 1
        elif "One of a Kind" in tab_param:    default_tab = 2
        elif "Weaver Onboarding" in tab_param: default_tab = 3
        st.query_params.clear()

    lang       = st.session_state.get("language", "en")
    tab_keys   = ["buyer", "weaver", "ooak", "onboard"]
    tab_labels = [
        get_ui_string("nav_buyer",   lang),
        get_ui_string("nav_weaver",  lang),
        get_ui_string("nav_ooak",    lang),
        get_ui_string("nav_onboard", lang),
    ]

    selected_label = st.radio(
        "Nav", tab_labels, horizontal=True,
        label_visibility="collapsed", index=default_tab,
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
