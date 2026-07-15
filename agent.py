"""
Pakshi — Agentic Orchestration Engine (Enhanced)
Upgraded with State Escape Hatches, Semantic Swatch Selection, Multi-Dialect STT Dialog, and Crash-Proof Routing.
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
    
    # Broadcast to up to 5 top candidates
    for i, (score, profile, wid) in enumerate(candidates[:5]):
        # Higher ranked weavers are more likely to accept the order
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

def _format_swatch(i: int, s: SwatchOption) -> str:
    """Null-safe swatch formatting helper."""
    loc = f"{s.weaver_cluster}, {s.weaver_state}" if s.weaver_cluster else str(s.weaver_state or "Traditional Cluster")
    tags = ", ".join(s.sensory_tags[:3]) if s.sensory_tags else "Handwoven, Artisanal"
    return (f"  [{i}] {s.weave_style or 'Handloom'} — {s.color or 'Assorted'}\n"
            f"      ₹{s.price_inr} | {s.delivery_days} days delivery\n"
            f"      Weaver: {s.weaver_name or 'Master Artisan'}, {loc} ⭐{s.weaver_rating}\n"
            f"      Feel: {tags}")

def _format_order_confirmation(order: Order) -> str:
    """Null-safe order confirmation formatting helper."""
    s = order.selected_swatch
    w = order.selected_weaver
    if not s or not w:
        return "✅ ORDER CONFIRMED — Processing details..."
    return (f"✅ ORDER CONFIRMED — #{order.order_id}\n\n"
            f"  Fabric  : {s.weave_style} ({s.color})\n"
            f"  Price   : ₹{s.price_inr}\n"
            f"  Weaver  : {w.weaver_name}, {w.weaver_cluster}\n"
            f"  Rating  : ⭐{w.weaver_rating}\n"
            f"  Delivery: {w.delivery_days} days\n")

class PakshiAgent:
    def __init__(self):
        self.session = ConversationSession()

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
                f"This order is already {state.value}. Please reset to start a new session.", 
                state, done=True
            )
        return self._respond("I didn't quite catch that. Could you rephrase what you are looking for?", state)

    def reset(self):
        self.session = ConversationSession()

    def _handle_collecting(self, user_input: str) -> dict:
        intent = parse_intent(user_input)
        self.session.intent = intent
        
        if intent.confidence < 0.5:
            self.session.low_confidence_strikes += 1
            if self.session.low_confidence_strikes >= 3:
                # Apply fallback defaults while preserving any successfully extracted parameters
                if not intent.occasion: intent.occasion = "casual"
                if not intent.budget: intent.budget = 1800
                if not intent.fabric: intent.fabric = ["cotton"]
                intent.confidence, intent.missing = self._compute_confidence_manually(intent)
            else:
                followup = build_followup_question(intent.missing) or "Could you share your budget or preferred fabric?"
                return self._respond(
                    f"I'd love to help find the perfect fabric! {followup}",
                    AgentState.COLLECTING,
                    data={"confidence": intent.confidence, "missing": intent.missing}
                )
                
        # Confidence sufficient — proceed to vector catalog retrieval
        return self._do_retrieval()

    def _do_retrieval(self) -> dict:
        intent = self.session.intent
        intent_dict = intent.to_dict() if intent else {}
        
        # Ensure raw_text is passed to retrieval for semantic enrichment
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
            
            swatch_lines = "\n\n".join(_format_swatch(i+1, s) for i, s in enumerate(options))
            budget_line = f"₹{intent.budget}" if intent and intent.budget else "your budget"
            loc_info = f" from {intent.location}" if intent and intent.location else ""
            
            msg = (f"Here are {len(options)} swatches that match your intent "
                   f"within {budget_line}{loc_info}:\n\n{swatch_lines}\n\n"
                   f"Reply with the option number (1 to {len(options)}) or name the color/weave to select.")
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
            return self._respond(
                result.get("agent_message", "Alternative options found. Reply YES to view."),
                AgentState.FALLBACK_PENDING,
                data={
                    "fallback_rule": result.get("fallback"),
                    "fallback_swatches": [asdict(s) for s in fallback_options]
                }
            )
        else:
            self.session.state = AgentState.FAILED
            return self._respond(
                result.get("agent_message", "No matching swatches found. We'll notify you when stock arrives."),
                AgentState.FAILED, done=True
            )

    def _handle_swatch_selection(self, user_input: str) -> dict:
        options = self.session.swatch_options
        if not options:
            self.session.state = AgentState.FAILED
            return self._respond("Session error: No swatches available to select.", AgentState.FAILED, done=True)

        text = user_input.lower().strip()
        selection = None

        # 1. Check for explicit numerical indices (e.g., "1", "option 2", "3rd")
        num_match = re.search(r'\b(\d+)\b', text)
        if num_match:
            val = int(num_match.group(1)) - 1
            if 0 <= val < len(options):
                selection = val

        # 2. Check for word numerals and Indic colloquial ordinals
        if selection is None:
            if any(w in text for w in ("1", "first", "one", "1st", "pehla", "modati")): selection = 0
            elif any(w in text for w in ("2", "second", "two", "2nd", "doosra", "rendava")) and len(options) >= 2: selection = 1
            elif any(w in text for w in ("3", "third", "three", "3rd", "teesra", "moodava")) and len(options) >= 3: selection = 2

        # 3. Semantic keyword matching against available swatch attributes
        if selection is None:
            for idx, opt in enumerate(options):
                # Match against color or weave name
                if (opt.color.lower() in text or opt.weave_style.lower() in text or 
                    opt.fabric_type.lower() in text):
                    selection = idx
                    break

        # 4. State Escape Hatch: If selection failed, check if user is refining their query intent
        if selection is None:
            new_intent = parse_intent(user_input)
            # If the new input contains distinct shopping entities (new budget, color, or location), re-route!
            if new_intent.confidence >= 0.40 or new_intent.budget or new_intent.color or new_intent.weave:
                self.session.intent = new_intent
                self.session.state = AgentState.COLLECTING
                return self._handle_collecting(user_input)
            
            return self._respond(
                f"Please reply with the option number (1 to {len(options)}) or name the color/weave you prefer.",
                AgentState.RETRIEVED
            )

        selected = options[selection]
        self.session.order = Order(
            order_id=f"PKS-{uuid.uuid4().hex[:6].upper()}",
            buyer_intent=self.session.intent.to_dict() if self.session.intent else {},
            selected_swatch=selected
        )
        self.session.state = AgentState.SWATCH_SELECTED
        
        msg = (f"✅ Swatch locked!\n\n  {selected.weave_style} — {selected.color}\n"
               f"  ₹{selected.price_inr} | {selected.delivery_days} days\n\n"
               "Broadcasting your order to qualified weavers...\n\n"
               "(Reply 'confirm' to proceed or 'back' to re-select)")
        return self._respond(msg, AgentState.SWATCH_SELECTED, data={"selected_swatch": asdict(selected)})

    def _handle_fallback_response(self, user_input: str) -> dict:
        text = user_input.lower().strip()
        # Natively recognizes English, Hinglish, Telugu, Tamil, and Bengali affirmatives/negatives
        yes_words = {"yes", "yeah", "yep", "haan", "ha", "ok", "okay", "sure", "go ahead", "theek hai", "ji haan", "sare", "avunu", "aam", "confirm", "proceed", "show"}
        no_words = {"no", "nahi", "nope", "nahin", "nah", "n", "don't", "dont", "wait", "vaddu", "oddu", "vendaam", "naa", "cancel", "stop"}

        if any(w in text for w in yes_words):
            options = self.session.swatch_options
            self.session.state = AgentState.RETRIEVED
            if not options:
                return self._respond("No fallback options available at this moment.", AgentState.FAILED, done=True)
                
            swatch_lines = "\n\n".join(_format_swatch(i+1, s) for i, s in enumerate(options))
            rule = self.session.fallback_rule or {}
            fab_name = str(rule.get('fallback_fabric', 'alternative')).replace('_', ' ')
            
            msg = (f"Great! Here are curated options featuring {fab_name}:\n\n"
                   f"{swatch_lines}\n\nReply with your preferred option number (1 to {len(options)}).")
            return self._respond(msg, AgentState.RETRIEVED, data={"swatches": [asdict(s) for s in options]})
            
        elif any(w in text for w in no_words):
            budget_val = self.session.intent.budget if self.session.intent else "your target budget"
            return self._respond(
                f"No problem. I'll save your preference for budget ₹{budget_val} "
                "and notify you the moment an artisanal weave matching your exact spec becomes available.",
                AgentState.FAILED, done=True
            )
        else:
            return self._respond("Please say YES to view these alternative fabric options or NO to wait.", AgentState.FALLBACK_PENDING)

    def _handle_post_selection(self, user_input: str) -> dict:
        text = user_input.lower().strip()
        back_words = {"back", "reselect", "change", "no", "nahi", "oddu", "vaddu", "return", "wait", "another"}
        
        if any(w in text for w in back_words):
            self.session.state = AgentState.RETRIEVED
            options = self.session.swatch_options
            swatch_lines = "\n\n".join(_format_swatch(i+1, s) for i, s in enumerate(options))
            return self._respond(
                f"No problem! Let's take another look at the options:\n\n{swatch_lines}\n\n"
                f"Reply with the number (1 to {len(options)}) of the swatch you'd like to lock.",
                AgentState.RETRIEVED
            )
            
        confirm_words = {"confirm", "yes", "proceed", "ok", "okay", "go ahead", "haan", "theek hai", "done", "sare", "avunu", "lock"}
        if not any(w in text for w in confirm_words):
            return self._respond("Reply 'confirm' to broadcast and place the order, or 'back' to choose a different swatch.", AgentState.SWATCH_SELECTED)

        # Execute Broadcast and select optimal weaver
        self.session.state = AgentState.BROADCASTING
        selected = self.session.order.selected_swatch if self.session.order else None
        if not selected:
            self.session.state = AgentState.FAILED
            return self._respond("Order error: Swatch details lost. Please reset session.", AgentState.FAILED, done=True)

        buyer_state = self.session.intent.location if self.session.intent else None
        broadcasts = _rank_weavers(selected, buyer_state=buyer_state)
        accepted = [b for b in broadcasts if b.accepted]
        
        if not accepted:
            self.session.state = AgentState.FAILED
            return self._respond(
                "We broadcasted to our network, but all specialized weavers for this specific craft are currently at capacity. We will notify you when a slot opens.", 
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
        msg = (f"📡 Broadcast sent to {len(broadcasts)} artisanal weavers.\n\n{summary}\n\n"
               f"Agent automatically routed your order to the optimal weaver based on craft specialty, rating & delivery speed.\n\n"
               f"{_format_order_confirmation(self.session.order)}")
               
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
