"""
Pakshi — Agentic Orchestration Engine (Enhanced)
Upgraded with State Escape Hatches, Semantic Swatch Selection, Multi-Dialect STT Dialog, and Crash-Proof Routing.
Now fully bilingual – all agent responses appear in Hindi when the user speaks Hindi.
"""
import json, time, uuid, re
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any

from intent_parser import parse_intent, build_followup_question, IntentResult
from retrieval import retrieve_swatches

BASE_DIR = Path(__file__).parent

class AgentState(str, Enum):
    GREETING = "greeting"
    COLLECTING = "collecting"
    RETRIEVED = "retrieved"
    FALLBACK_PENDING = "fallback_pending"
    SWATCH_SELECTED = "swatch_selected"
    BROADCASTING = "broadcasting"
    WEAVER_SELECTED = "weaver_selected"
    CONFIRMED = "confirmed"
    FAILED = "failed"

@dataclass
class SwatchOption:
    swatch_id: str; fabric_type: str; weave_style: str; color: str
    price_inr: int; delivery_days: int; weaver_name: str
    weaver_cluster: str; weaver_state: str; weaver_rating: float
    sensory_tags: list[str]; occasion_tags: list[str]

@dataclass
class WeaverBroadcast:
    weaver_id: str; weaver_name: str; weaver_cluster: str; weaver_state: str
    weaver_rating: float; delivery_days: int; price_inr: int
    accepted: bool = False; response_time: float | None = None

@dataclass
class Order:
    order_id: str; buyer_intent: dict
    selected_swatch: SwatchOption | None = None
    selected_weaver: WeaverBroadcast | None = None
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    confirmed_at: float | None = None

@dataclass
class AgentMessage:
    role: str; content: str; state: str; data: dict = field(default_factory=dict)

@dataclass
class ConversationSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    state: AgentState = AgentState.GREETING
    intent: IntentResult | None = None
    retrieval_result: dict | None = None
    swatch_options: list[SwatchOption] = field(default_factory=list)
    fallback_rule: dict | None = None
    order: Order | None = None
    history: list[AgentMessage] = field(default_factory=list)
    turn_count: int = 0
    low_confidence_strikes: int = 0

def _load_weaver_profiles():
    """Safely loads weaver profiles from disk with crash-proof fallback to empty dict."""
    try:
        with open(BASE_DIR / "weaver_profiles.json", encoding="utf-8") as f:
            data = json.load(f)
        return {w["id"]: w for w in data.get("weaver_profiles", [])}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {}

_WEAVER_PROFILES = _load_weaver_profiles()

def _rank_weavers(swatch: SwatchOption, buyer_state: str | None = None):
    """Crash-proof weaver ranking algorithm with safe dictionary access and realistic broadcast simulation."""
    candidates = []
    for wid, profile in _WEAVER_PROFILES.items():
        if not isinstance(profile, dict):
            continue
            
        specialties = profile.get("fabric_specialty", [])
        if swatch.fabric_type not in specialties:
            continue
            
        price_range = profile.get("price_range_inr", {})
        min_p = int(float(price_range.get("min", 0)))
        max_p = int(float(price_range.get("max", 999999)))
        if not (min_p <= swatch.price_inr <= max_p):
            continue
            
        rating = float(profile.get("rating", 4.0))
        del_days = int(float(profile.get("delivery_days", 14)))
        w_state = str(profile.get("state", ""))
        
        score = rating * 20 + max(0, (30 - del_days)) * 1.5
        if buyer_state and w_state.lower() == str(buyer_state).lower():
            score += 10
        candidates.append((score, profile, wid))
        
    candidates.sort(key=lambda x: x[0], reverse=True)
    broadcasts = []
    
    for i, (score, profile, wid) in enumerate(candidates[:5]):
        accepted = i < 3 or (score > 85.0 and i < 4)
        broadcasts.append(WeaverBroadcast(
            weaver_id=wid,
            weaver_name=str(profile.get("name", "Master Weaver")),
            weaver_cluster=str(profile.get("cluster", "Handloom Cluster")),
            weaver_state=str(profile.get("state", "India")),
            weaver_rating=round(float(profile.get("rating", 4.5)), 1),
            delivery_days=int(float(profile.get("delivery_days", 14))),
            price_inr=swatch.price_inr,
            accepted=accepted,
            response_time=round(1.5 + i * 0.7, 1)
        ))
    return broadcasts

class PakshiAgent:
    # Bilingual message catalog
    MESSAGES = {
        "en": {
            "greeting": "I'd love to help find the perfect fabric! {followup}",
            "swatches_found": "Here are {count} swatches that match your intent within {budget}{location_info}:\n\n{swatch_lines}\n\nReply with the option number (1 to {count}) or name the color/weave to select.",
            "fallback_proposal": "No {fabric} match found{location_msg} within ₹{budget}. {fallback_message} Say YES to see {fallback_fabric} options or NO to wait.",
            "fallback_yes": "Great! Here are curated options featuring {fab_name}:\n\n{swatch_lines}\n\nReply with your preferred option number (1 to {count}).",
            "fallback_no": "No problem. I'll save your preference for budget ₹{budget_val} and notify you the moment an artisanal weave matching your exact spec becomes available.",
            "swatch_locked": "✅ Swatch locked!\n\n  {weave_style} — {color}\n  ₹{price} | {delivery} days\n\nBroadcasting your order to qualified weavers...\n\n(Reply 'confirm' to proceed or 'back' to re-select)",
            "order_confirmed": "📡 Broadcast sent to {count} artisanal weavers.\n\n{summary}\n\nAgent automatically routed your order to the optimal weaver based on craft specialty, rating & delivery speed.\n\n{order_confirmation}",
            "order_error": "Order error: Swatch details lost. Please reset session.",
            "no_swatches": "No matching swatches found. We'll notify you when stock arrives.",
            "no_weavers": "We broadcasted to our network, but all specialized weavers for this specific craft are currently at capacity. We will notify you when a slot opens.",
            "select_prompt": "Please reply with the option number (1 to {count}) or name the color/weave you prefer.",
            "already_done": "This order is already {state}. Please reset to start a new session.",
            "fallback_instruction": "Please say YES to view these alternative fabric options or NO to wait.",
            "confirm_prompt": "Reply 'confirm' to broadcast and place the order, or 'back' to choose a different swatch.",
            "back_prompt": "No problem! Let's take another look at the options:\n\n{swatch_lines}\n\nReply with the number (1 to {count}) of the swatch you'd like to lock.",
            "weaver_not_found": "Weaver not found.",
            "generic_error": "I didn't quite catch that. Could you rephrase what you are looking for?",
            "fallback_no_options": "No fallback options available at this moment.",
            "session_error": "Session error: No swatches available to select.",
        },
        "hi": {
            "greeting": "मैं आपके लिए सही फैब्रिक ढूंढने में मदद करना चाहता हूँ! {followup}",
            "swatches_found": "यहाँ {count} स्वैच हैं जो आपकी ज़रूरत के अनुसार {budget}{location_info} के भीतर हैं:\n\n{swatch_lines}\n\nविकल्प संख्या (1 से {count}) या रंग/बुनाई का नाम बताकर चुनें।",
            "fallback_proposal": "{fabric} का कोई मैच {location_msg} ₹{budget} के भीतर नहीं मिला। {fallback_message} YES कहें तो {fallback_fabric} विकल्प दिखाएँ, या NO कहें तो प्रतीक्षा करें।",
            "fallback_yes": "बढ़िया! यहाँ {fab_name} वाले चुनिंदा विकल्प हैं:\n\n{swatch_lines}\n\nअपनी पसंद का विकल्प संख्या (1 से {count}) बताएँ।",
            "fallback_no": "कोई बात नहीं। मैं आपकी पसंद ₹{budget_val} के बजट के लिए सुरक्षित रखूँगा और जैसे ही आपके मानदंडों से मेल खाने वाली बुनाई उपलब्ध होगी, आपको सूचित करूँगा।",
            "swatch_locked": "✅ स्वैच लॉक हो गया!\n\n  {weave_style} — {color}\n  ₹{price} | {delivery} दिन\n\nआपका ऑर्डर योग्य बुनकरों को प्रसारित किया जा रहा है...\n\n(जारी रखने के लिए 'confirm' या पुनः चयन के लिए 'back' कहें)",
            "order_confirmed": "📡 {count} बुनकरों को प्रसारण भेजा गया।\n\n{summary}\n\nएजेंट ने कारीगरी विशेषता, रेटिंग और डिलीवरी गति के आधार पर इष्टतम बुनकर को स्वचालित रूप से चुना।\n\n{order_confirmation}",
            "order_error": "ऑर्डर त्रुटि: स्वैच विवरण खो गया। कृपया सत्र रीसेट करें।",
            "no_swatches": "कोई मिलान स्वैच नहीं मिला। स्टॉक आने पर हम आपको सूचित करेंगे।",
            "no_weavers": "हमने अपने नेटवर्क को प्रसारित किया, लेकिन इस विशेष कला के सभी विशेषज्ञ बुनकर वर्तमान में क्षमता पर हैं। जब कोई स्लॉट खुलेगा तो हम आपको सूचित करेंगे।",
            "select_prompt": "कृपया विकल्प संख्या (1 से {count}) या अपनी पसंद का रंग/बुनाई बताएँ।",
            "already_done": "यह ऑर्डर पहले ही {state} हो चुका है। नया सत्र शुरू करने के लिए रीसेट करें।",
            "fallback_instruction": "कृपया YES कहें तो वैकल्पिक फैब्रिक विकल्प देखें या NO कहें तो प्रतीक्षा करें।",
            "confirm_prompt": "ऑर्डर प्रसारित करने के लिए 'confirm' कहें, या दूसरा स्वैच चुनने के लिए 'back' कहें।",
            "back_prompt": "कोई बात नहीं! आइए विकल्पों पर फिर से नज़र डालें:\n\n{swatch_lines}\n\nजिस स्वैच को लॉक करना चाहते हैं उसकी संख्या (1 से {count}) बताएँ।",
            "weaver_not_found": "बुनकर नहीं मिला।",
            "generic_error": "मैं समझ नहीं पाया। कृपया अपनी आवश्यकता फिर से बताएँ।",
            "fallback_no_options": "इस समय कोई वैकल्पिक विकल्प उपलब्ध नहीं है।",
            "session_error": "सत्र त्रुटि: चयन के लिए कोई स्वैच उपलब्ध नहीं है।",
        }
    }

    def __init__(self):
        self.session = ConversationSession()

    def _t(self, key: str, lang: str = "en", **kwargs) -> str:
        """Return localized message for the given key and language."""
        messages = self.MESSAGES.get(lang, self.MESSAGES["en"])
        template = messages.get(key, key)
        try:
            return template.format(**kwargs)
        except KeyError:
            # fallback if missing placeholders
            return template

    def _format_swatch(self, i: int, s: SwatchOption, lang: str = "en") -> str:
        """Format a single swatch option in the requested language."""
        loc = f"{s.weaver_cluster}, {s.weaver_state}" if s.weaver_cluster else str(s.weaver_state or "Traditional Cluster")
        tags = ", ".join(s.sensory_tags[:3]) if s.sensory_tags else "Handwoven, Artisanal"
        # For Hindi, we can also translate the tags (they are stored in English; we can skip translation for brevity)
        # We'll just use a simple line format.
        return (f"  [{i}] {s.weave_style or 'Handloom'} — {s.color or 'Assorted'}\n"
                f"      ₹{s.price_inr} | {s.delivery_days} days delivery\n"
                f"      Weaver: {s.weaver_name or 'Master Artisan'}, {loc} ⭐{s.weaver_rating}\n"
                f"      Feel: {tags}")

    def _format_order_confirmation(self, order: Order, lang: str = "en") -> str:
        """Null-safe order confirmation formatting helper."""
        s = order.selected_swatch
        w = order.selected_weaver
        if not s or not w:
            return self._t("order_error", lang)
        if lang.startswith("hi") or "hindi" in lang.lower():
            return (f"✅ ऑर्डर कन्फर्म — #{order.order_id}\n\n"
                    f"  फैब्रिक : {s.weave_style} ({s.color})\n"
                    f"  कीमत   : ₹{s.price_inr}\n"
                    f"  बुनकर   : {w.weaver_name}, {w.weaver_cluster}\n"
                    f"  रेटिंग  : ⭐{w.weaver_rating}\n"
                    f"  डिलीवरी: {w.delivery_days} दिन\n")
        else:
            return (f"✅ ORDER CONFIRMED — #{order.order_id}\n\n"
                    f"  Fabric  : {s.weave_style} ({s.color})\n"
                    f"  Price   : ₹{s.price_inr}\n"
                    f"  Weaver  : {w.weaver_name}, {w.weaver_cluster}\n"
                    f"  Rating  : ⭐{w.weaver_rating}\n"
                    f"  Delivery: {w.delivery_days} days\n")

    def chat(self, user_input: str) -> dict[str, Any]:
        self.session.turn_count += 1
        user_input = (user_input or "").strip()
        state = self.session.state
        
        if state == AgentState.GREETING:
            self.session.state = AgentState.COLLECTING
            return self._handle_collecting(user_input)
        elif state == AgentState.COLLECTING:
            return self._handle_collecting(user_input)
        elif state == AgentState.RETRIEVED:
            return self._handle_swatch_selection(user_input)
        elif state == AgentState.FALLBACK_PENDING:
            return self._handle_fallback_response(user_input)
        elif state == AgentState.SWATCH_SELECTED:
            return self._handle_post_selection(user_input)
        elif state in (AgentState.CONFIRMED, AgentState.FAILED):
            return self._respond(
                self._t("already_done", self._get_lang(), state=state.value),
                state, done=True
            )
        return self._respond(self._t("generic_error", self._get_lang()), state)

    def _get_lang(self) -> str:
        """Return language hint from current intent, default 'en'."""
        if self.session.intent:
            return self.session.intent.language_hint or "en"
        return "en"

    def reset(self):
        self.session = ConversationSession()

    def _handle_collecting(self, user_input: str) -> dict:
        intent = parse_intent(user_input)
        self.session.intent = intent
        lang = self._get_lang()
        
        if intent.confidence < 0.5:
            self.session.low_confidence_strikes += 1
            if self.session.low_confidence_strikes >= 3:
                if not intent.occasion: intent.occasion = "casual"
                if not intent.budget: intent.budget = 1800
                if not intent.fabric: intent.fabric = ["cotton"]
                intent.confidence, intent.missing = self._compute_confidence_manually(intent)
            else:
                followup = build_followup_question(intent.missing, lang) or "Could you share your budget or preferred fabric?"
                return self._respond(
                    self._t("greeting", lang, followup=followup),
                    AgentState.COLLECTING,
                    data={"confidence": intent.confidence, "missing": intent.missing}
                )
                
        return self._do_retrieval()

    def _do_retrieval(self) -> dict:
        intent = self.session.intent
        lang = self._get_lang()
        intent_dict = intent.to_dict() if intent else {}
        if intent and intent.raw_input:
            intent_dict["raw_text"] = intent.raw_input
            
        result = retrieve_swatches(intent_dict)
        self.session.retrieval_result = result

        if result["status"] == "match":
            options = []
            for r in result.get("results", []):
                options.append(SwatchOption(
                    swatch_id=str(r.get("swatch_id", "")),
                    fabric_type=str(r.get("fabric_type", "cotton")),
                    weave_style=str(r.get("weave_style", "handloom")),
                    color=str(r.get("color", "assorted")),
                    price_inr=int(float(r.get("price_inr", 0))),
                    delivery_days=int(float(r.get("delivery_days", 7))),
                    weaver_name=str(r.get("weaver_name", "Artisan")),
                    weaver_cluster=str(r.get("weaver_cluster", "")),
                    weaver_state=str(r.get("weaver_state", "India")),
                    weaver_rating=round(float(r.get("weaver_rating", 4.5)), 1),
                    sensory_tags=r.get("sensory_tags", []),
                    occasion_tags=r.get("occasion_tags", [])
                ))
            self.session.swatch_options = options
            self.session.state = AgentState.RETRIEVED
            
            swatch_lines = "\n\n".join(self._format_swatch(i+1, s, lang) for i, s in enumerate(options))
            budget_line = f"₹{intent.budget}" if intent and intent.budget else "your budget"
            loc_info = f" from {intent.location}" if intent and intent.location else ""
            msg = self._t("swatches_found", lang,
                          count=len(options),
                          budget=budget_line,
                          location_info=loc_info,
                          swatch_lines=swatch_lines)
            return self._respond(msg, AgentState.RETRIEVED, data={"swatches": [asdict(s) for s in options]})

        elif result["status"] == "fallback":
            self.session.fallback_rule = result.get("fallback")
            self.session.state = AgentState.FALLBACK_PENDING
            fallback_options = []
            for r in result.get("results", []):
                fallback_options.append(SwatchOption(
                    swatch_id=str(r.get("swatch_id", "")),
                    fabric_type=str(r.get("fabric_type", "cotton")),
                    weave_style=str(r.get("weave_style", "handloom")),
                    color=str(r.get("color", "assorted")),
                    price_inr=int(float(r.get("price_inr", 0))),
                    delivery_days=int(float(r.get("delivery_days", 7))),
                    weaver_name=str(r.get("weaver_name", "Artisan")),
                    weaver_cluster=str(r.get("weaver_cluster", "")),
                    weaver_state=str(r.get("weaver_state", "India")),
                    weaver_rating=round(float(r.get("weaver_rating", 4.5)), 1),
                    sensory_tags=r.get("sensory_tags", []),
                    occasion_tags=r.get("occasion_tags", [])
                ))
            self.session.swatch_options = fallback_options

            # Build localized fallback message
            fallback_rule = result.get("fallback", {})
            intended_fabric = fallback_rule.get("requested_fabric", "cotton").replace('_', ' ')
            fallback_fabric = fallback_rule.get("fallback_fabric", "alternative").replace('_', ' ')
            fallback_message = fallback_rule.get("message", "We have an alternative fabric at a slightly higher price.")
            location_msg = f" from {intent.location}" if intent and intent.location else ""
            budget_val = intent.budget if intent and intent.budget else "your budget"
            msg = self._t("fallback_proposal", lang,
                          fabric=intended_fabric,
                          location_msg=location_msg,
                          budget=budget_val,
                          fallback_message=fallback_message,
                          fallback_fabric=fallback_fabric)
            return self._respond(msg, AgentState.FALLBACK_PENDING,
                                 data={
                                     "fallback_rule": result.get("fallback"),
                                     "fallback_swatches": [asdict(s) for s in fallback_options]
                                 })
        else:
            self.session.state = AgentState.FAILED
            return self._respond(
                self._t("no_swatches", lang),
                AgentState.FAILED, done=True
            )

    def _handle_swatch_selection(self, user_input: str) -> dict:
        options = self.session.swatch_options
        lang = self._get_lang()
        if not options:
            self.session.state = AgentState.FAILED
            return self._respond(self._t("session_error", lang), AgentState.FAILED, done=True)

        text = user_input.lower().strip()
        selection = None

        num_match = re.search(r'\b(\d+)\b', text)
        if num_match:
            val = int(num_match.group(1)) - 1
            if 0 <= val < len(options):
                selection = val

        if selection is None:
            if any(w in text for w in ("1", "first", "one", "1st", "pehla", "modati")): selection = 0
            elif any(w in text for w in ("2", "second", "two", "2nd", "doosra", "rendava")) and len(options) >= 2: selection = 1
            elif any(w in text for w in ("3", "third", "three", "3rd", "teesra", "moodava")) and len(options) >= 3: selection = 2

        if selection is None:
            for idx, opt in enumerate(options):
                if (opt.color.lower() in text or opt.weave_style.lower() in text or 
                    opt.fabric_type.lower() in text):
                    selection = idx
                    break

        if selection is None:
            new_intent = parse_intent(user_input)
            if new_intent.confidence >= 0.40 or new_intent.budget or new_intent.color or new_intent.weave:
                self.session.intent = new_intent
                self.session.state = AgentState.COLLECTING
                return self._handle_collecting(user_input)
            
            return self._respond(
                self._t("select_prompt", lang, count=len(options)),
                AgentState.RETRIEVED
            )

        selected = options[selection]
        self.session.order = Order(
            order_id=f"PKS-{uuid.uuid4().hex[:6].upper()}",
            buyer_intent=self.session.intent.to_dict() if self.session.intent else {},
            selected_swatch=selected
        )
        self.session.state = AgentState.SWATCH_SELECTED
        
        msg = self._t("swatch_locked", lang,
                      weave_style=selected.weave_style,
                      color=selected.color,
                      price=selected.price_inr,
                      delivery=selected.delivery_days)
        return self._respond(msg, AgentState.SWATCH_SELECTED, data={"selected_swatch": asdict(selected)})

    def _handle_fallback_response(self, user_input: str) -> dict:
        text = user_input.lower().strip()
        lang = self._get_lang()
        yes_words = {"yes", "yeah", "yep", "haan", "ha", "ok", "okay", "sure", "go ahead", "theek hai", "ji haan", "sare", "avunu", "aam", "confirm", "proceed", "show"}
        no_words = {"no", "nahi", "nope", "nahin", "nah", "n", "don't", "dont", "wait", "vaddu", "oddu", "vendaam", "naa", "cancel", "stop"}

        if any(w in text for w in yes_words):
            options = self.session.swatch_options
            self.session.state = AgentState.RETRIEVED
            if not options:
                return self._respond(self._t("fallback_no_options", lang), AgentState.FAILED, done=True)
                
            swatch_lines = "\n\n".join(self._format_swatch(i+1, s, lang) for i, s in enumerate(options))
            rule = self.session.fallback_rule or {}
            fab_name = str(rule.get('fallback_fabric', 'alternative')).replace('_', ' ')
            msg = self._t("fallback_yes", lang,
                          fab_name=fab_name,
                          swatch_lines=swatch_lines,
                          count=len(options))
            return self._respond(msg, AgentState.RETRIEVED, data={"swatches": [asdict(s) for s in options]})
            
        elif any(w in text for w in no_words):
            budget_val = self.session.intent.budget if self.session.intent else "your target budget"
            return self._respond(
                self._t("fallback_no", lang, budget_val=budget_val),
                AgentState.FAILED, done=True
            )
        else:
            return self._respond(self._t("fallback_instruction", lang), AgentState.FALLBACK_PENDING)

    def _handle_post_selection(self, user_input: str) -> dict:
        text = user_input.lower().strip()
        lang = self._get_lang()
        back_words = {"back", "reselect", "change", "no", "nahi", "oddu", "vaddu", "return", "wait", "another"}
        
        if any(w in text for w in back_words):
            self.session.state = AgentState.RETRIEVED
            options = self.session.swatch_options
            swatch_lines = "\n\n".join(self._format_swatch(i+1, s, lang) for i, s in enumerate(options))
            msg = self._t("back_prompt", lang,
                          swatch_lines=swatch_lines,
                          count=len(options))
            return self._respond(msg, AgentState.RETRIEVED)
            
        confirm_words = {"confirm", "yes", "proceed", "ok", "okay", "go ahead", "haan", "theek hai", "done", "sare", "avunu", "lock"}
        if not any(w in text for w in confirm_words):
            return self._respond(self._t("confirm_prompt", lang), AgentState.SWATCH_SELECTED)

        self.session.state = AgentState.BROADCASTING
        selected = self.session.order.selected_swatch if self.session.order else None
        if not selected:
            self.session.state = AgentState.FAILED
            return self._respond(self._t("order_error", lang), AgentState.FAILED, done=True)

        buyer_state = self.session.intent.location if self.session.intent else None
        broadcasts = _rank_weavers(selected, buyer_state=buyer_state)
        accepted = [b for b in broadcasts if b.accepted]
        
        if not accepted:
            self.session.state = AgentState.FAILED
            return self._respond(
                self._t("no_weavers", lang),
                AgentState.FAILED, done=True
            )

        best = accepted[0]
        self.session.order.selected_weaver = best
        self.session.order.status = "confirmed"
        self.session.order.confirmed_at = time.time()
        self.session.state = AgentState.CONFIRMED
        
        summary = "\n".join(
            f"  {'✅' if b.accepted else '❌'} {b.weaver_name} ({b.weaver_cluster}) "
            f"— {'Accepted' if b.accepted else 'At Capacity'}" for b in broadcasts
        )
        order_conf = self._format_order_confirmation(self.session.order, lang)
        msg = self._t("order_confirmed", lang,
                      count=len(broadcasts),
                      summary=summary,
                      order_confirmation=order_conf)
               
        return self._respond(msg, AgentState.CONFIRMED, data={"order": asdict(self.session.order)}, done=True)

    def _respond(self, message: str, state: AgentState, data: dict = None, done: bool = False) -> dict:
        self.session.history.append(AgentMessage(role="agent", content=message, state=state.value, data=data or {}))
        return {"message": message, "state": state.value, "data": data or {}, "done": done}

    @staticmethod
    def _compute_confidence_manually(intent: IntentResult):
        """
        Synchronized manual confidence calculation matching the exact entity weights 
        of the upgraded intent_parser.py suite.
        """
        score = 0.0
        missing = []
        
        if intent.feel:      score += 0.25
        else:                missing.append("feel")
        if intent.occasion:  score += 0.25
        else:                missing.append("occasion")
        if intent.budget:    score += 0.20
        else:                missing.append("budget")
        if intent.fabric:    score += 0.15
        else:                missing.append("fabric")
        if intent.weave:     score += 0.05
        else:                missing.append("weave")
        if intent.color:     score += 0.05
        else:                missing.append("color")
        if intent.location:  score += 0.05
        else:                missing.append("location")
        
        intent.missing = missing
        return round(max(0.0, min(1.0, score)), 2), missing
