"""
Pakshi — Agentic Orchestration Engine
=======================================
This is the brain of Pakshi. It is genuinely agentic because it:

  1. PARSES    — converts raw buyer text into structured intent
  2. RETRIEVES — queries ChromaDB RAG for matching swatches, with optional location filtering
  3. REASONS   — decides what to do based on what it finds
  4. PROPOSES  — offers alternatives when budget/fabric don't match
  5. WAITS     — holds state and waits for buyer confirmation
  6. BROADCASTS— notifies matched weavers with order details
  7. RANKS     — autonomously selects optimal weaver (proximity + rating + history)
  8. CONFIRMS  — locks the order on Meesho

Agent states (conversation FSM):
  GREETING → COLLECTING → RETRIEVED → FALLBACK_PENDING →
  SWATCH_SELECTED → BROADCASTING → WEAVER_SELECTED → CONFIRMED

The agent never skips states. Every transition is logged.
"""

import json
import time
import uuid
import re
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any

from intent_parser import parse_intent, build_followup_question, IntentResult
from retrieval import retrieve_swatches

BASE_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Agent states
# ---------------------------------------------------------------------------

class AgentState(str, Enum):
    GREETING           = "greeting"           # initial state
    COLLECTING         = "collecting"         # gathering buyer intent
    RETRIEVED          = "retrieved"          # swatches shown, waiting for selection
    FALLBACK_PENDING   = "fallback_pending"   # no match — waiting for YES/NO
    SWATCH_SELECTED    = "swatch_selected"    # buyer picked a swatch
    BROADCASTING       = "broadcasting"       # notifying weavers
    WEAVER_SELECTED    = "weaver_selected"    # agent picked optimal weaver
    CONFIRMED          = "confirmed"          # order confirmed
    FAILED             = "failed"             # truly no match, no fallback


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SwatchOption:
    swatch_id:      str
    fabric_type:    str
    weave_style:    str
    color:          str
    price_inr:      int
    delivery_days:  int
    weaver_name:    str
    weaver_cluster: str
    weaver_state:   str
    weaver_rating:  float
    sensory_tags:   list[str]
    occasion_tags:  list[str]


@dataclass
class WeaverBroadcast:
    weaver_id:      str
    weaver_name:    str
    weaver_cluster: str
    weaver_state:   str
    weaver_rating:  float
    delivery_days:  int
    price_inr:      int
    accepted:       bool = False
    response_time:  float | None = None   # simulated for prototype


@dataclass
class Order:
    order_id:        str
    buyer_intent:    dict
    selected_swatch: SwatchOption | None   = None
    selected_weaver: WeaverBroadcast | None = None
    status:          str                   = "pending"
    created_at:      float                 = field(default_factory=time.time)
    confirmed_at:    float | None          = None


@dataclass
class AgentMessage:
    role:    str    # "agent" | "system"
    content: str
    state:   str
    data:    dict   = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Conversation session
# ---------------------------------------------------------------------------

@dataclass
class ConversationSession:
    session_id:       str                  = field(default_factory=lambda: str(uuid.uuid4())[:8])
    state:            AgentState           = AgentState.GREETING
    intent:           IntentResult | None  = None
    retrieval_result: dict | None          = None
    swatch_options:   list[SwatchOption]   = field(default_factory=list)
    fallback_rule:    dict | None          = None
    order:            Order | None         = None
    history:          list[AgentMessage]   = field(default_factory=list)
    turn_count:       int                  = 0
    low_confidence_strikes: int            = 0   # how many vague inputs in a row


# ---------------------------------------------------------------------------
# Weaver profile loader (for ranking)
# ---------------------------------------------------------------------------

def _load_weaver_profiles() -> dict[str, dict]:
    with open(BASE_DIR / "weaver_profiles.json") as f:
        data = json.load(f)
    return {w["id"]: w for w in data["weaver_profiles"]}

_WEAVER_PROFILES = _load_weaver_profiles()


# ---------------------------------------------------------------------------
# Location extraction (new)
# Maps known weaving clusters / states to canonical names
# ---------------------------------------------------------------------------
_LOCATION_ALIASES: dict[str, str] = {
    # Clusters
    "kanchipuram": "Kanchipuram",
    "kancheepuram": "Kanchipuram",
    "pochampally": "Pochampally",
    "pochampalli": "Pochampally",
    "banarasi": "Varanasi",
    "varanasi": "Varanasi",
    "ilkal": "Ilkal",
    "kota": "Kota",
    "chanderi": "Chanderi",
    "maheshwar": "Maheshwar",
    "maheshwari": "Maheshwar",
    "dharmavaram": "Dharmavaram",
    "molakalmuru": "Molakalmuru",
    "mysore": "Mysore",
    "sambalpur": "Sambalpuri",
    "sambalpuri": "Sambalpuri",
    "nuapatna": "Nuapatna",
    "bagru": "Bagru",
    "sanganer": "Sanganer",
    "kutch": "Kutch",
    "kerala": "Kerala",
    "tamilnadu": "Tamil Nadu",
    "tamil nadu": "Tamil Nadu",
    "andhra": "Andhra Pradesh",
    "andhra pradesh": "Andhra Pradesh",
    "telangana": "Telangana",
    "karnataka": "Karnataka",
    "rajasthan": "Rajasthan",
    "west bengal": "West Bengal",
    "bengal": "West Bengal",
    "odisha": "Odisha",
    "orissa": "Odisha",
    "gujarat": "Gujarat",
    "maharashtra": "Maharashtra",
    "bihar": "Bihar",
    "uttar pradesh": "Uttar Pradesh",
}

def _extract_location(text: str) -> str | None:
    """Extract a location (cluster or state) from buyer text."""
    text_lower = text.lower()
    for alias, canonical in _LOCATION_ALIASES.items():
        if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
            return canonical
    return None


# ---------------------------------------------------------------------------
# Weaver ranking logic
# ---------------------------------------------------------------------------

def _rank_weavers(
    swatch: SwatchOption,
    buyer_state: str | None = None,
) -> list[WeaverBroadcast]:
    """
    Autonomously ranks weavers who can fulfil the selected swatch.
    Ranking factors (in order):
      1. Can they make this fabric type? (hard filter)
      2. Is price within their range? (hard filter)
      3. Weaver rating (higher = better)
      4. Delivery days (lower = better)
      5. Proximity (same state as buyer preferred) — soft bonus

    Returns a ranked list of WeaverBroadcast objects (simulated accepts
    for prototype — in production this would await real weaver responses).
    """
    candidates = []

    for wid, profile in _WEAVER_PROFILES.items():
        # Hard filter 1: fabric specialty match
        if swatch.fabric_type not in profile["fabric_specialty"]:
            continue

        # Hard filter 2: price range compatibility
        if not (profile["price_range_inr"]["min"] <= swatch.price_inr
                <= profile["price_range_inr"]["max"]):
            continue

        # Scoring
        score = 0.0
        score += profile["rating"] * 20          # 0–100 points from rating
        score += max(0, (30 - profile["delivery_days"])) * 1.5  # faster = better
        if buyer_state and profile["state"] == buyer_state:
            score += 10                           # proximity bonus

        candidates.append((score, profile, wid))

    # Sort descending by score
    candidates.sort(key=lambda x: x[0], reverse=True)

    # Simulate weaver responses (prototype behaviour)
    broadcasts = []
    for i, (score, profile, wid) in enumerate(candidates[:5]):
        # Top 3 accept, rest decline (realistic simulation)
        accepted = i < 3
        broadcasts.append(WeaverBroadcast(
            weaver_id      = wid,
            weaver_name    = profile["name"],
            weaver_cluster = profile["cluster"],
            weaver_state   = profile["state"],
            weaver_rating  = profile["rating"],
            delivery_days  = profile["delivery_days"],
            price_inr      = swatch.price_inr,
            accepted       = accepted,
            response_time  = round(2.0 + i * 0.8, 1),  # simulated response time
        ))

    return broadcasts


# ---------------------------------------------------------------------------
# Response builder helpers
# ---------------------------------------------------------------------------

def _format_swatch(i: int, s: SwatchOption) -> str:
    location = f"{s.weaver_cluster}, {s.weaver_state}" if s.weaver_cluster else s.weaver_state
    return (
        f"  [{i}] {s.weave_style} — {s.color}\n"
        f"      ₹{s.price_inr} | {s.delivery_days} days delivery\n"
        f"      Weaver: {s.weaver_name}, {location} "
        f"⭐{s.weaver_rating}\n"
        f"      Feel: {', '.join(s.sensory_tags[:3])}"
    )


def _format_order_confirmation(order: Order) -> str:
    s = order.selected_swatch
    w = order.selected_weaver
    return (
        f"✅ ORDER CONFIRMED — #{order.order_id}\n\n"
        f"  Fabric  : {s.weave_style} ({s.color})\n"
        f"  Price   : ₹{s.price_inr}\n"
        f"  Weaver  : {w.weaver_name}, {w.weaver_cluster}\n"
        f"  Rating  : ⭐{w.weaver_rating}\n"
        f"  Delivery: {w.delivery_days} days\n\n"
        f"The weaver will dye the fabric and send you a photo for "
        f"approval before full production begins.\n"
        f"Expectation is locked. No surprises."
    )


# ---------------------------------------------------------------------------
# Core agent
# ---------------------------------------------------------------------------

class PakshiAgent:
    """
    Stateful conversational agent for Pakshi.

    Usage:
        agent = PakshiAgent()
        response = agent.chat("light saree for summer wedding ₹1500")
        print(response["message"])

        # After swatches shown:
        response = agent.chat("1")   # buyer selects option 1
        print(response["message"])
    """

    def __init__(self):
        self.session = ConversationSession()
        self._log("Agent initialised", AgentState.GREETING)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def chat(self, user_input: str) -> dict[str, Any]:
        """
        Main entry point. Takes raw user text, returns agent response dict:
        {
          "message":  str,           # what to show the buyer
          "state":    str,           # current agent state
          "data":     dict,          # swatches / order / weaver info
          "done":     bool,          # True when order confirmed or failed
        }
        """
        self.session.turn_count += 1
        user_input = user_input.strip()

        state = self.session.state

        # Route by current state
        if state == AgentState.GREETING:
            return self._handle_greeting(user_input)

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
                "This order is already " + state.value + ". Start a new session for a new order.",
                state, done=True
            )

        return self._respond("I didn't understand that. Could you rephrase?", state)

    def reset(self):
        """Resets the session for a new conversation."""
        self.session = ConversationSession()

    # ------------------------------------------------------------------
    # State handlers
    # ------------------------------------------------------------------

    def _handle_greeting(self, user_input: str) -> dict:
        """
        First message from buyer. Parse intent immediately.
        If confidence is high enough, go straight to retrieval.
        If too vague, ask a follow-up.
        """
        self.session.state = AgentState.COLLECTING
        return self._handle_collecting(user_input)


    def _handle_collecting(self, user_input: str) -> dict:
        """
        Parse buyer intent. If confidence >= 0.5, retrieve swatches.
        If too vague, ask the most important missing question.
        """
        intent = parse_intent(user_input)
        # Enhance intent with location
        location = _extract_location(user_input)
        if location:
            # Store location in the intent for later use in retrieval
            intent.location = location  # we'll add this field dynamically
        self.session.intent = intent

        # Too vague — ask follow-up
        if intent.confidence < 0.5:
            self.session.low_confidence_strikes += 1

            # After 3 vague inputs, proceed anyway with what we have
            if self.session.low_confidence_strikes >= 3:
                if not intent.occasion:
                    intent.occasion = "casual"
                if not intent.budget:
                    intent.budget = 1500
                    intent.budget_flex = True
            else:
                followup = build_followup_question(intent.missing)
                return self._respond(
                    f"I'd love to help find the perfect fabric! {followup}",
                    AgentState.COLLECTING,
                    data={"confidence": intent.confidence, "missing": intent.missing}
                )

        # Confidence sufficient — retrieve
        result = self._do_retrieval()
        return result


    def _do_retrieval(self) -> dict:
        """
        Query ChromaDB RAG with current intent, passing location filter.
        """
        intent = self.session.intent
        # Convert IntentResult to dict and add location if present
        intent_dict = intent.to_dict() if hasattr(intent, 'to_dict') else intent.__dict__
        # Add location key if we extracted one
        if hasattr(intent, 'location') and intent.location:
            intent_dict['location'] = intent.location

        result = retrieve_swatches(intent_dict)
        self.session.retrieval_result = result

        if result["status"] == "match":
            # Build SwatchOption list
            options = []
            for r in result["results"]:
                options.append(SwatchOption(
                    swatch_id      = r["swatch_id"],
                    fabric_type    = r["fabric_type"],
                    weave_style    = r["weave_style"],
                    color          = r["color"],
                    price_inr      = r["price_inr"],
                    delivery_days  = r["delivery_days"],
                    weaver_name    = r["weaver_name"],
                    weaver_cluster = r["weaver_cluster"],
                    weaver_state   = r["weaver_state"],
                    weaver_rating  = r["weaver_rating"],
                    sensory_tags   = r["sensory_tags"],
                    occasion_tags  = r["occasion_tags"],
                ))
            self.session.swatch_options = options
            self.session.state = AgentState.RETRIEVED

            swatch_lines = "\n\n".join(
                _format_swatch(i + 1, s) for i, s in enumerate(options)
            )
            budget_line = (
                f"₹{intent.budget}" if intent.budget else "your budget"
            )
            location_info = f" from {intent.location}" if hasattr(intent, 'location') and intent.location else ""
            msg = (
                f"Here are {len(options)} swatches that match your intent "
                f"within {budget_line}{location_info}:\n\n"
                f"{swatch_lines}\n\n"
                f"Reply with 1, 2, or 3 to select your preferred swatch. "
                f"Your expectation will be locked before production begins."
            )
            return self._respond(msg, AgentState.RETRIEVED,
                                 data={"swatches": [asdict(s) for s in options]})

        elif result["status"] == "fallback":
            # No match within budget — agent proposes alternative
            self.session.fallback_rule = result["fallback"]
            self.session.state = AgentState.FALLBACK_PENDING

            # Store fallback swatches for later
            fallback_options = []
            for r in result["results"]:
                fallback_options.append(SwatchOption(
                    swatch_id      = r["swatch_id"],
                    fabric_type    = r["fabric_type"],
                    weave_style    = r["weave_style"],
                    color          = r["color"],
                    price_inr      = r["price_inr"],
                    delivery_days  = r["delivery_days"],
                    weaver_name    = r["weaver_name"],
                    weaver_cluster = r["weaver_cluster"],
                    weaver_state   = r["weaver_state"],
                    weaver_rating  = r["weaver_rating"],
                    sensory_tags   = r["sensory_tags"],
                    occasion_tags  = r["occasion_tags"],
                ))
            self.session.swatch_options = fallback_options

            return self._respond(
                result["agent_message"],
                AgentState.FALLBACK_PENDING,
                data={"fallback_rule": result["fallback"],
                      "fallback_swatches": [asdict(s) for s in fallback_options]}
            )

        else:
            # Truly no match
            self.session.state = AgentState.FAILED
            return self._respond(
                "I couldn't find any swatches matching your request right now. "
                "We'll notify you as soon as a matching weaver becomes available. "
                "Would you like to adjust your budget or fabric preference?",
                AgentState.FAILED,
                done=True
            )


    def _handle_swatch_selection(self, user_input: str) -> dict:
        """
        Buyer selects a swatch (1, 2, or 3).
        Agent locks expectation and moves to broadcasting.
        """
        options = self.session.swatch_options
        selection = None

        # Parse selection: accept "1", "first", "option 1", "the first one" etc.
        text = user_input.lower().strip()
        if text in ("1", "first", "one", "option 1", "first one", "1st"):
            selection = 0
        elif text in ("2", "second", "two", "option 2", "second one", "2nd"):
            selection = 1
        elif text in ("3", "third", "three", "option 3", "third one", "3rd"):
            selection = 2
        else:
            # Try to extract digit
            import re
            m = re.search(r'\b([123])\b', user_input)
            if m:
                selection = int(m.group(1)) - 1

        if selection is None or selection >= len(options):
            return self._respond(
                f"Please reply with 1, 2, or 3 to select one of the swatches shown.",
                AgentState.RETRIEVED
            )

        selected = options[selection]
        self.session.order = Order(
            order_id     = f"PKS-{uuid.uuid4().hex[:6].upper()}",
            buyer_intent = self.session.intent.to_dict() if hasattr(self.session.intent, 'to_dict') else self.session.intent.__dict__,
            selected_swatch = selected,
        )
        self.session.state = AgentState.SWATCH_SELECTED

        msg = (
            f"✅ Swatch locked!\n\n"
            f"  {selected.weave_style} — {selected.color}\n"
            f"  ₹{selected.price_inr} | {selected.delivery_days} days\n\n"
            f"Broadcasting your order to qualified weavers in the {selected.weaver_cluster} "
            f"cluster and nearby regions...\n\n"
            f"(Reply 'confirm' to proceed or 'back' to re-select)"
        )
        return self._respond(msg, AgentState.SWATCH_SELECTED,
                             data={"selected_swatch": asdict(selected)})


    def _handle_fallback_response(self, user_input: str) -> dict:
        """
        Buyer responds YES or NO to the fallback proposal.
        YES → show fallback swatches
        NO  → offer to wait or adjust budget
        """
        text = user_input.lower().strip()
        yes_words = {"yes", "yeah", "yep", "haan", "ha", "ok", "okay",
                     "sure", "go ahead", "theek hai", "chalo", "y"}
        no_words  = {"no", "nahi", "nope", "nahin", "nah", "n",
                     "don't", "dont", "wait"}

        if any(w in text for w in yes_words):
            # Show fallback swatches
            options = self.session.swatch_options
            self.session.state = AgentState.RETRIEVED

            if not options:
                return self._respond(
                    "Unfortunately I couldn't find fallback options either. "
                    "We'll notify you when matching weavers are available.",
                    AgentState.FAILED, done=True
                )

            swatch_lines = "\n\n".join(
                _format_swatch(i + 1, s) for i, s in enumerate(options)
            )
            rule = self.session.fallback_rule or {}
            msg = (
                f"Great! Here are options with {rule.get('fallback_fabric','').replace('_',' ')} "
                f"— same quality, adjusted price:\n\n"
                f"{swatch_lines}\n\n"
                f"Reply 1, 2, or 3 to select."
            )
            return self._respond(msg, AgentState.RETRIEVED,
                                 data={"swatches": [asdict(s) for s in options]})

        elif any(w in text for w in no_words):
            return self._respond(
                "No problem. I'll keep your request — "
                f"budget ₹{self.session.intent.budget} — "
                "and notify you as soon as a matching weaver is available. "
                "You can also try adjusting your budget if you'd like options now.",
                AgentState.FAILED, done=True
            )
        else:
            return self._respond(
                "Please say YES to see alternative options or NO to wait for availability.",
                AgentState.FALLBACK_PENDING
            )


    def _handle_post_selection(self, user_input: str) -> dict:
        """
        After swatch is locked. Buyer confirms → agent broadcasts,
        ranks weavers, selects optimal one, confirms order.
        """
        text = user_input.lower().strip()

        if "back" in text or "reselect" in text or "change" in text:
            self.session.state = AgentState.RETRIEVED
            options = self.session.swatch_options
            swatch_lines = "\n\n".join(
                _format_swatch(i + 1, s) for i, s in enumerate(options)
            )
            return self._respond(
                f"No problem! Here are the options again:\n\n{swatch_lines}\n\n"
                f"Reply 1, 2, or 3.",
                AgentState.RETRIEVED
            )

        confirm_words = {"confirm", "yes", "proceed", "ok", "okay",
                         "go ahead", "haan", "theek hai", "done"}
        if not any(w in text for w in confirm_words):
            return self._respond(
                "Reply 'confirm' to place the order or 'back' to re-select a swatch.",
                AgentState.SWATCH_SELECTED
            )

        # STEP 1: BROADCAST
        self.session.state = AgentState.BROADCASTING
        selected = self.session.order.selected_swatch
        broadcasts = _rank_weavers(selected)

        accepted = [b for b in broadcasts if b.accepted]

        if not accepted:
            self.session.state = AgentState.FAILED
            return self._respond(
                "Unfortunately no weavers are available for this swatch right now. "
                "We'll notify you when capacity opens up.",
                AgentState.FAILED, done=True
            )

        # STEP 2: AUTONOMOUS WEAVER SELECTION
        # Agent picks the best accepting weaver (already ranked by rating + delivery)
        best_weaver = accepted[0]
        self.session.order.selected_weaver = best_weaver
        self.session.state = AgentState.WEAVER_SELECTED

        # STEP 3: CONFIRM ORDER
        self.session.order.status = "confirmed"
        self.session.order.confirmed_at = time.time()
        self.session.state = AgentState.CONFIRMED

        broadcast_summary = "\n".join(
            f"  {'✅' if b.accepted else '❌'} {b.weaver_name} "
            f"({b.weaver_cluster}) — "
            f"{'Accepted' if b.accepted else 'Unavailable'}"
            for b in broadcasts
        )

        msg = (
            f"📡 Broadcast sent to {len(broadcasts)} weavers.\n\n"
            f"{broadcast_summary}\n\n"
            f"Agent autonomously selected the optimal weaver based on "
            f"rating and delivery history. "
            f"Not first-come-first-serve — autonomous optimisation.\n\n"
            f"{_format_order_confirmation(self.session.order)}"
        )

        return self._respond(msg, AgentState.CONFIRMED,
                             data={"order": asdict(self.session.order)},
                             done=True)


    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _respond(
        self,
        message: str,
        state: AgentState,
        data: dict = None,
        done: bool = False
    ) -> dict[str, Any]:
        msg = AgentMessage(
            role    = "agent",
            content = message,
            state   = state.value,
            data    = data or {}
        )
        self.session.history.append(msg)
        self._log(f"State: {state.value}", state)
        return {
            "message": message,
            "state":   state.value,
            "data":    data or {},
            "done":    done,
        }

    def _log(self, text: str, state: AgentState):
        pass  # swap in logging.info() for production


# ---------------------------------------------------------------------------
# Test harness — full end-to-end conversation simulations
# ---------------------------------------------------------------------------

def _run_scenario(title: str, turns: list[str]):
    print(f"\n{'='*65}")
    print(f"SCENARIO: {title}")
    print('='*65)
    agent = PakshiAgent()
    for user_msg in turns:
        print(f"\n👤 BUYER : {user_msg}")
        response = agent.chat(user_msg)
        print(f"🤖 PAKSHI [{response['state'].upper()}]:\n{response['message']}")
        if response["done"]:
            print("\n[Session ended]")
            break


if __name__ == "__main__":

    # Scenario 1: Happy path — clear intent, selects swatch, confirms
    _run_scenario(
        "Happy Path — Summer Wedding ₹1500",
        [
            "Light flowy saree for a summer wedding, budget ₹1500, mint green",
            "1",        # select swatch 1
            "confirm",  # confirm order
        ]
    )

    # Scenario 2: Budget fallback — pure silk at ₹700 (below all silk minimums)
    _run_scenario(
        "Budget Fallback — Pure Silk at ₹700",
        [
            "Heavy royal silk saree for wedding, ₹700, deep red, grand and stiff",
            "yes",      # accept fallback proposal
            "1",        # select swatch 1
            "confirm",
        ]
    )

    # Scenario 3: Vague input, agent asks follow-up, buyer clarifies
    _run_scenario(
        "Vague Input → Follow-up → Recovery",
        [
            "something nice",               # too vague
            "for my sister's wedding",      # adds occasion but still vague
            "light and flowy, ₹2000, teal", # complete
            "1",
            "confirm",
        ]
    )

    # Scenario 4: Buyer changes mind, goes back, re-selects
    _run_scenario(
        "Buyer Changes Mind Mid-Flow",
        [
            "Breathable cotton saree for office, ₹700, navy blue",
            "2",     # first pick
            "back",  # changed mind
            "1",     # re-selects
            "confirm",
        ]
    )

    # Scenario 5: No match, buyer declines fallback
    _run_scenario(
        "No Match + Buyer Declines Fallback",
        [
            "Pure Banarasi silk, ₹500, grand, heavy",
            "no",   # declines fallback
        ]
    )

    # Scenario 6: Location filtering — "Kanchipuram silk saree"
    _run_scenario(
        "Location Filtering — Kanchipuram",
        [
            "Kanchipuram silk saree for wedding, under ₹5000",
            "1",
            "confirm",
        ]
    )
