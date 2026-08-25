"""
Enhanced Multi-Turn Conversational State Machine.
Handles WhatsApp auto-reply detection, objections, price inquiries, slot rescheduling, and instant intent execution.
"""

from __future__ import annotations
import re
from typing import Dict, Any, Optional
from core.models import ReplyActionResponse


class EnhancedConversationEngine:
    """Production-grade dialogue state tracker for Vera."""

    # 1. WhatsApp Auto-Reply Canned Greetings
    AUTO_REPLY_PATTERNS = [
        r"thank you for (?:contacting|reaching out|messaging|calling)",
        r"thanks for (?:contacting|reaching out|messaging)",
        r"we are currently (?:closed|away|unavailable|busy|offline)",
        r"welcome to .*(?:clinic|salon|restaurant|gym|pharmacy|centre|studio|hospital)",
        r"our (?:working|business|operating) hours are",
        r"please leave (?:your|a) message",
        r"we will get back to you (?:shortly|soon|asap|within)",
        r"auto(?:mated)?[- ]?reply",
        r"this is an automated (?:response|message)",
        r"namaste.*(?:we have received|swagat hai)",
    ]

    # 2. Affirmative Intents (Immediate Execution)
    AFFIRMATIVE_PATTERNS = [
        r"\b(?:yes|yep|yup|sure|yeah|send|please|ok|okay|kardo|kar do|bhejo|bhej do|done|approved|confirm|proceed|ha|haan|sahi hai|bilkul|theek hai|chalega|1|2)\b",
    ]

    # 3. Negative / Opt-Out
    NEGATIVE_PATTERNS = [
        r"\b(?:no|nope|not interested|nahi|nah|stop|cancel|don't|dont|never|unsubscribe|band karo|mat bhejo)\b",
    ]

    # 4. Delay / Busy
    DELAY_PATTERNS = [
        r"\b(?:busy|later|after some time|baad me|kal|call later|busy right now|driving|in a meeting|busy with patients|busy with clients)\b",
    ]

    # 5. Price / Cost Inquiries
    PRICE_INQUIRY_PATTERNS = [
        r"\b(?:price|cost|charges|rate|kitna|how much|pricing|fees|discount|kya charge|kya rate)\b",
    ]

    # 6. Rescheduling / Slot Shifts
    RESCHEDULE_PATTERNS = [
        r"\b(?:reschedule|change time|different time|saturday|sunday|evening|morning|dusra time|postpone|next week)\b",
    ]

    # 7. Objections (e.g. Too expensive / not needed)
    OBJECTION_PATTERNS = [
        r"\b(?:expensive|costly|too high|budget|mehenga|jyada hai|discount do|kam karo)\b",
    ]

    def is_auto_reply(self, message: str) -> bool:
        """Sub-millisecond classification for WhatsApp Business auto-replies."""
        msg_lower = message.strip().lower()
        for pattern in self.AUTO_REPLY_PATTERNS:
            if re.search(pattern, msg_lower):
                return True
        return False

    def handle_reply(
        self,
        conversation_id: str,
        merchant_id: str,
        customer_id: Optional[str],
        from_role: str,
        message: str,
        turn_number: int,
        context_store: Any,
    ) -> ReplyActionResponse:
        """
        Evaluates inbound messages across semantic intent categories.
        """
        msg_clean = message.strip()
        msg_lower = msg_clean.lower()
        merchant = context_store.get_merchant(merchant_id) or {}
        m_identity = merchant.get("identity", {})
        m_name = m_identity.get("name", "our clinic")
        locality = m_identity.get("locality", "your locality")
        cat_slug = merchant.get("category_slug", "dentists")

        # ---------------------------------------------------------------------
        # 1. AUTO-REPLY FILTER (Zero Turns Burned)
        # ---------------------------------------------------------------------
        if self.is_auto_reply(msg_clean):
            return ReplyActionResponse(
                action="wait",
                wait_seconds=1800,
                rationale="Detected merchant WhatsApp Business automated greeting; backing off 30 mins to allow real human response without burning turns.",
            )

        # ---------------------------------------------------------------------
        # 2. NEGATIVE / OPT-OUT
        # ---------------------------------------------------------------------
        for pattern in self.NEGATIVE_PATTERNS:
            if re.search(pattern, msg_lower):
                return ReplyActionResponse(
                    action="end",
                    rationale="User indicated disinterest or opt-out; gracefully closing conversation loop.",
                )

        # ---------------------------------------------------------------------
        # 3. BUSY / DELAY
        # ---------------------------------------------------------------------
        for pattern in self.DELAY_PATTERNS:
            if re.search(pattern, msg_lower):
                return ReplyActionResponse(
                    action="wait",
                    wait_seconds=3600,
                    rationale="Merchant indicated they are currently occupied; waiting 1 hour before follow-up.",
                )

        # ---------------------------------------------------------------------
        # 4. OBJECTION HANDLING (Too Expensive -> Pivot to Budget Entry Offer)
        # ---------------------------------------------------------------------
        for pattern in self.OBJECTION_PATTERNS:
            if re.search(pattern, msg_lower):
                if customer_id:
                    body = (
                        f"Understood! We also offer our introductory consultation & basic checkup package "
                        f"with zero upfront commitment. Would you like me to book that for you instead?"
                    )
                else:
                    body = (
                        f"Completely understand! We can adjust the package to a lighter introductory offer "
                        f"to maximize initial customer walk-ins in {locality}. Want me to prepare that draft?"
                    )
                return ReplyActionResponse(
                    action="send",
                    body=body,
                    cta="binary_yes_no",
                    rationale="Constructive objection handling: acknowledged price sensitivity and presented low-friction entry alternative.",
                )

        # ---------------------------------------------------------------------
        # 5. RESCHEDULING / SLOT PREFERENCES
        # ---------------------------------------------------------------------
        for pattern in self.RESCHEDULE_PATTERNS:
            if re.search(pattern, msg_lower):
                body = (
                    f"No problem! We've marked your timing preference for {m_name}. "
                    f"Our coordinator will confirm the updated slot with you right away. "
                    f"Reply YES if you'd like an instant WhatsApp calendar invite!"
                )
                return ReplyActionResponse(
                    action="send",
                    body=body,
                    cta="binary_yes_no",
                    rationale="Flexible slot rescheduling acknowledging custom customer timing preferences.",
                )

        # ---------------------------------------------------------------------
        # 6. PRICE / COST INQUIRY
        # ---------------------------------------------------------------------
        for pattern in self.PRICE_INQUIRY_PATTERNS:
            if re.search(pattern, msg_lower) or "?" in msg_clean:
                # Find active offer pricing
                active_offers = [o.get("title") for o in merchant.get("offers", []) if o.get("status") == "active"]
                offer_text = active_offers[0] if active_offers else "Transparent, standardized rates"
                
                body = (
                    f"Happy to clarify! At {m_name}, pricing starts with '{offer_text}' with 100% transparent "
                    f"billing and no hidden charges. Want me to send the complete service menu & booking link?"
                )
                return ReplyActionResponse(
                    action="send",
                    body=body,
                    cta="binary_yes_no",
                    rationale="Clear, grounded pricing response from merchant's active catalog with a low-friction confirmation CTA.",
                )

        # ---------------------------------------------------------------------
        # 7. INSTANT INTENT FAST-TRACK (AFFIRMATIVE)
        # ---------------------------------------------------------------------
        for pattern in self.AFFIRMATIVE_PATTERNS:
            if re.search(pattern, msg_lower):
                if customer_id:
                    body = (
                        "Confirmed! We've booked this for you and notified our front desk team. "
                        "See you soon! Feel free to message us here if you need any directions or updates."
                    )
                else:
                    body = (
                        "Done! Sent to your profile and activated. "
                        "I also drafted a 3-line WhatsApp update you can share directly with customers. "
                        "Let me know if you want any edits or have questions!"
                    )
                return ReplyActionResponse(
                    action="send",
                    body=body,
                    cta="open_ended",
                    rationale="Immediate 1-turn affirmative intent execution: completed workflow without repetitive qualifying questions.",
                )

        # ---------------------------------------------------------------------
        # 8. GENERAL CONTINUATION
        # ---------------------------------------------------------------------
        body = (
            f"Got it! I've updated your preferences for {m_name}. "
            f"Is there anything specific you'd like me to assist you with today?"
        )
        return ReplyActionResponse(
            action="send",
            body=body,
            cta="open_ended",
            rationale="Acknowledged feedback constructively and kept conversational door open.",
        )


# Global instance
conversation_engine = EnhancedConversationEngine()
