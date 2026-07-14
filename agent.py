"""
Pakshi — Agentic Orchestration Engine (Enhanced)
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
    with open(BASE_DIR / "weaver_profiles.json") as f:
        return {w["id"]: w for w in json.load(f)["weaver_profiles"]}
_WEAVER_PROFILES = _load_weaver_profiles()

def _rank_weavers(swatch: SwatchOption, buyer_state: str | None = None):
    candidates = []
    for wid, profile in _WEAVER_PROFILES.items():
        if swatch.fabric_type not in profile["fabric_specialty"]:
            continue
        if not (profile["price_range_inr"]["min"] <= swatch.price_inr <= profile["price_range_inr"]["max"]):
            continue
        score = profile["rating"] * 20 + max(0, (30 - profile["delivery_days"])) * 1.5
        if buyer_state and profile["state"] == buyer_state:
            score += 10
        candidates.append((score, profile, wid))
    candidates.sort(key=lambda x: x[0], reverse=True)
    broadcasts = []
    for i, (score, profile, wid) in enumerate(candidates[:5]):
        accepted = i < 3
        broadcasts.append(WeaverBroadcast(
            weaver_id=wid, weaver_name=profile["name"],
            weaver_cluster=profile["cluster"], weaver_state=profile["state"],
            weaver_rating=profile["rating"], delivery_days=profile["delivery_days"],
            price_inr=swatch.price_inr, accepted=accepted,
            response_time=round(2.0 + i*0.8, 1)
        ))
    return broadcasts

def _format_swatch(i: int, s: SwatchOption) -> str:
    loc = f"{s.weaver_cluster}, {s.weaver_state}" if s.weaver_cluster else s.weaver_state
    return (f"  [{i}] {s.weave_style} — {s.color}\n"
            f"      ₹{s.price_inr} | {s.delivery_days} days delivery\n"
            f"      Weaver: {s.weaver_name}, {loc} ⭐{s.weaver_rating}\n"
            f"      Feel: {', '.join(s.sensory_tags[:3])}")

def _format_order_confirmation(order: Order) -> str:
    s = order.selected_swatch; w = order.selected_weaver
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
        user_input = user_input.strip()
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
            return self._respond("This order is already " + state.value + ". Start a new session.", state, done=True)
        return self._respond("I didn't understand. Could you rephrase?", state)

    def reset(self):
        self.session = ConversationSession()

    def _handle_collecting(self, user_input: str) -> dict:
        intent = parse_intent(user_input)
        self.session.intent = intent
        if intent.confidence < 0.5:
            self.session.low_confidence_strikes += 1
            if self.session.low_confidence_strikes >= 3:
                if not intent.occasion: intent.occasion = "casual"
                if not intent.budget: intent.budget = 1500
                # Recalculate confidence
                intent.confidence, intent.missing = self._compute_confidence_manually(intent)
            else:
                followup = build_followup_question(intent.missing)
                return self._respond(f"I'd love to help find the perfect fabric! {followup}",
                                     AgentState.COLLECTING,
                                     data={"confidence": intent.confidence, "missing": intent.missing})
        # Confidence sufficient – retrieve
        return self._do_retrieval()

    def _do_retrieval(self) -> dict:
        intent = self.session.intent
        intent_dict = intent.to_dict()  # includes location
        result = retrieve_swatches(intent_dict)
        self.session.retrieval_result = result

        if result["status"] == "match":
            options = []
            for r in result["results"]:
                options.append(SwatchOption(
                    swatch_id=r["swatch_id"], fabric_type=r["fabric_type"],
                    weave_style=r["weave_style"], color=r["color"],
                    price_inr=r["price_inr"], delivery_days=r["delivery_days"],
                    weaver_name=r["weaver_name"], weaver_cluster=r["weaver_cluster"],
                    weaver_state=r["weaver_state"], weaver_rating=r["weaver_rating"],
                    sensory_tags=r["sensory_tags"], occasion_tags=r["occasion_tags"]
                ))
            self.session.swatch_options = options
            self.session.state = AgentState.RETRIEVED
            swatch_lines = "\n\n".join(_format_swatch(i+1, s) for i, s in enumerate(options))
            budget_line = f"₹{intent.budget}" if intent.budget else "your budget"
            loc_info = f" from {intent.location}" if intent.location else ""
            msg = (f"Here are {len(options)} swatches that match your intent "
                   f"within {budget_line}{loc_info}:\n\n{swatch_lines}\n\n"
                   "Reply with 1, 2, or 3 to select.")
            return self._respond(msg, AgentState.RETRIEVED, data={"swatches": [asdict(s) for s in options]})

        elif result["status"] == "fallback":
            self.session.fallback_rule = result["fallback"]
            self.session.state = AgentState.FALLBACK_PENDING
            fallback_options = []
            for r in result["results"]:
                fallback_options.append(SwatchOption(
                    swatch_id=r["swatch_id"], fabric_type=r["fabric_type"],
                    weave_style=r["weave_style"], color=r["color"],
                    price_inr=r["price_inr"], delivery_days=r["delivery_days"],
                    weaver_name=r["weaver_name"], weaver_cluster=r["weaver_cluster"],
                    weaver_state=r["weaver_state"], weaver_rating=r["weaver_rating"],
                    sensory_tags=r["sensory_tags"], occasion_tags=r["occasion_tags"]
                ))
            self.session.swatch_options = fallback_options
            return self._respond(result["agent_message"], AgentState.FALLBACK_PENDING,
                                 data={"fallback_rule": result["fallback"],
                                       "fallback_swatches": [asdict(s) for s in fallback_options]})
        else:
            self.session.state = AgentState.FAILED
            return self._respond(result["agent_message"], AgentState.FAILED, done=True)

    def _handle_swatch_selection(self, user_input: str) -> dict:
        options = self.session.swatch_options
        text = user_input.lower().strip()
        selection = None
        if text in ("1","first","one","option 1","1st"): selection = 0
        elif text in ("2","second","two","option 2","2nd"): selection = 1
        elif text in ("3","third","three","option 3","3rd"): selection = 2
        else:
            m = re.search(r'\b([123])\b', user_input)
            if m: selection = int(m.group(1)) - 1
        if selection is None or selection >= len(options):
            return self._respond("Please reply with 1, 2, or 3.", AgentState.RETRIEVED)
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
        yes = {"yes","yeah","yep","haan","ha","ok","okay","sure","go ahead","theek hai"}
        no = {"no","nahi","nope","nahin","nah","n","don't","dont","wait"}
        if any(w in text for w in yes):
            options = self.session.swatch_options
            self.session.state = AgentState.RETRIEVED
            if not options:
                return self._respond("No fallback options available.", AgentState.FAILED, done=True)
            swatch_lines = "\n\n".join(_format_swatch(i+1, s) for i, s in enumerate(options))
            rule = self.session.fallback_rule or {}
            msg = (f"Great! Here are options with {rule.get('fallback_fabric','').replace('_',' ')}:\n\n"
                   f"{swatch_lines}\n\nReply 1, 2, or 3 to select.")
            return self._respond(msg, AgentState.RETRIEVED, data={"swatches": [asdict(s) for s in options]})
        elif any(w in text for w in no):
            return self._respond(
                f"No problem. I'll keep your request — budget ₹{self.session.intent.budget} — "
                "and notify you when a matching weaver is available.",
                AgentState.FAILED, done=True)
        else:
            return self._respond("Please say YES to see alternatives or NO to wait.", AgentState.FALLBACK_PENDING)

    def _handle_post_selection(self, user_input: str) -> dict:
        text = user_input.lower().strip()
        if "back" in text or "reselect" in text or "change" in text:
            self.session.state = AgentState.RETRIEVED
            options = self.session.swatch_options
            swatch_lines = "\n\n".join(_format_swatch(i+1, s) for i, s in enumerate(options))
            return self._respond(f"No problem! Here are the options again:\n\n{swatch_lines}\n\nReply 1, 2, or 3.",
                                 AgentState.RETRIEVED)
        confirm = {"confirm","yes","proceed","ok","okay","go ahead","haan","theek hai","done"}
        if not any(w in text for w in confirm):
            return self._respond("Reply 'confirm' to place the order or 'back' to re‑select.",
                                 AgentState.SWATCH_SELECTED)
        # Broadcast and select
        self.session.state = AgentState.BROADCASTING
        selected = self.session.order.selected_swatch
        broadcasts = _rank_weavers(selected)
        accepted = [b for b in broadcasts if b.accepted]
        if not accepted:
            self.session.state = AgentState.FAILED
            return self._respond("No weavers available. We'll notify you later.", AgentState.FAILED, done=True)
        best = accepted[0]
        self.session.order.selected_weaver = best
        self.session.order.status = "confirmed"
        self.session.order.confirmed_at = time.time()
        self.session.state = AgentState.CONFIRMED
        summary = "\n".join(f"  {'✅' if b.accepted else '❌'} {b.weaver_name} ({b.weaver_cluster}) "
                            f"— {'Accepted' if b.accepted else 'Unavailable'}" for b in broadcasts)
        msg = (f"📡 Broadcast sent to {len(broadcasts)} weavers.\n\n{summary}\n\n"
               f"Agent selected optimal weaver based on rating & delivery.\n\n"
               f"{_format_order_confirmation(self.session.order)}")
        return self._respond(msg, AgentState.CONFIRMED, data={"order": asdict(self.session.order)}, done=True)

    def _respond(self, message: str, state: AgentState, data: dict = None, done: bool = False) -> dict:
        self.session.history.append(AgentMessage(role="agent", content=message, state=state.value, data=data or {}))
        return {"message": message, "state": state.value, "data": data or {}, "done": done}

    @staticmethod
    def _compute_confidence_manually(intent: IntentResult):
        score = 0.0; missing = []
        if intent.feel: score += 0.40
        else: missing.append("feel")
        if intent.occasion: score += 0.30
        else: missing.append("occasion")
        if intent.budget: score += 0.20
        else: missing.append("budget")
        if intent.color: score += 0.05
        else: missing.append("color")
        if intent.location: score += 0.05
        else: missing.append("location")
        intent.missing = missing
        return round(score, 2), missing
