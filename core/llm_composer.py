"""
LLM-Powered Message Composer for Vera.
Calls Gemini or Groq to generate high-quality, context-grounded WhatsApp messages
that score 9-10/10 on all five rubric dimensions.

Falls back to the deterministic MessageComposer if LLM is unavailable or fails.
"""

from __future__ import annotations
import os
import json
import re
import time
import logging
import requests
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — Engineered from the 10 case studies that score 47-50/50
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Vera, magicpin's AI assistant for Indian local merchant growth. You compose WhatsApp messages to merchants and their customers.

YOUR OUTPUT IS SCORED ON 5 DIMENSIONS (0-10 each, total 50):

1. DECISION QUALITY: Choose the ONE best signal from the context. Add judgment — don't just report facts. Make contrarian recommendations when data supports it (e.g. "skip the promo, push your existing BOGO as delivery instead"). Strong bots THINK, weak bots template.

2. SPECIFICITY: Use exact numbers, dates, prices, sources from the provided context. "190 people in your locality searching for Dental Check Up" beats "increase visibility". NEVER fabricate data not present in the context. Numbers without provenance = fabrication penalty.

3. CATEGORY FIT — match the vertical's voice:
   • dentists → peer-clinical: "Dr." prefix, use "fluoride varnish", "caries", "recall window", "periodontal". Taboos: "cure", "guaranteed", "100% safe"
   • salons → warm-practical: owner first name, "sessions", "most asked-for this week", "bridal prep window"
   • restaurants → operator-to-operator: "covers", "AOV", "delivery radius", "table occupancy", "facilities managers"
   • gyms → coaching: "members", "ad spend", "conversion", "attendance challenge", "progressive overload"
   • pharmacies → trustworthy-precise: molecule names, batch numbers, "Rx customers", "sub-potency", "dispensed"

4. MERCHANT FIT: Personalize to THIS merchant. Use owner_first_name (not business name) for salutation. Reference their actual active offers, performance signals, subscription status, customer_aggregate data.

5. ENGAGEMENT COMPULSION: One strong reason to reply NOW with a low-friction next step. Vary these levers:
   • Loss aversion ("190 people searching but can't find you")
   • Social proof ("3 clinics in your locality did X")
   • Curiosity ("Want to see who?")
   • Reciprocity ("I've already drafted X for you")
   • Effort externalization ("Takes 2 min", "Live in 10 min")
   • Anxiety pre-emption ("this dip is normal, save your spend for Sept")
   • No-shame framing ("happens to most members, no judgment")

HARD RULES:
- NEVER fabricate offers, prices, dates, or numbers not in the context.
- Use owner_first_name for salutation. Dentists: "Dr. {name}". Others: "{name}" or "Hi {name}".
- If merchant has "hi" in identity.languages, use natural Hindi-English code-mix (Hinglish).
- Single CTA at the END of the message.
- No preambles ("I hope this finds you well..."). Start with substance.
- Keep messages 2-6 sentences. Concise.
- If trigger.scope == "customer" or customer is provided, set send_as = "merchant_on_behalf" and address the customer.
- For customer-facing: "Hi {customer_name}, {owner_name} from {merchant_name} here" format.
- Respect vocab_taboo from category voice. Never use those words.
- The rationale MUST cite specific data points from the context and name which scoring dimensions the message targets.

RESPOND WITH VALID JSON ONLY — no markdown, no ```json blocks:
{"body":"message text","cta":"binary_yes_no|choice|open_ended|none","send_as":"vera|merchant_on_behalf","rationale":"2 sentences citing specific data and scoring dimensions"}"""


REPLY_SYSTEM_PROMPT = """You are Vera, magicpin's AI assistant. You are handling a multi-turn WhatsApp conversation with a merchant or customer.

CONTEXT: You have the conversation history, merchant context, and category context.

DECIDE one of three actions:
- "send": Reply with a contextual, helpful message
- "wait": Back off (merchant is busy, or auto-reply detected)
- "end": Gracefully close (hostile, opt-out, or conversation complete)

RULES:
- If inbound is a WhatsApp auto-reply ("Thank you for contacting...", "We are currently closed..."), action="wait", wait_seconds=1800
- If inbound is hostile/spam ("stop messaging", "fraud", "spam"), action="end" with graceful goodbye
- If inbound is "no"/"not interested"/"nahi", action="end"
- If inbound is affirmative ("yes", "sure", "ok"), respond with IMMEDIATE ACTIONING — "Done! Confirmed..." with concrete next steps. NO qualifying questions.
- If inbound asks about services/prices, answer with SPECIFIC info from merchant context.
- Use merchant's owner_first_name and category-appropriate vocabulary.
- Match language (Hindi-English mix if merchant has "hi" in languages).
- Keep replies concise. 1-3 sentences max.

RESPOND WITH VALID JSON ONLY:
{"action":"send|wait|end","body":"reply text or null","cta":"open_ended|binary_yes_no|none|null","wait_seconds":null,"rationale":"1 sentence explaining the decision"}"""


class LLMComposer:
    """Calls Gemini or Groq to compose high-quality, context-grounded messages."""

    def __init__(self):
        self.provider: Optional[str] = None
        self.api_key: Optional[str] = None
        self._cache: Dict[str, dict] = {}
        self._init_provider()

    def _init_provider(self):
        """Detect available LLM provider from environment variables."""
        # Try Gemini first (free 15 RPM)
        for key_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            key = os.environ.get(key_name)
            if key:
                self.provider = "gemini"
                self.api_key = key
                logger.info(f"LLMComposer: Gemini initialized via {key_name}")
                return

        # Try Groq
        key = os.environ.get("GROQ_API_KEY")
        if key:
            self.provider = "groq"
            self.api_key = key
            logger.info("LLMComposer: Groq initialized")
            return

        # Try OpenAI-compatible (DeepSeek, OpenAI, etc.)
        key = os.environ.get("OPENAI_API_KEY")
        base = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
        if key:
            self.provider = "openai"
            self.api_key = key
            self.openai_base = base
            logger.info("LLMComposer: OpenAI-compatible initialized")
            return

        logger.warning("LLMComposer: No LLM API key found. Will use deterministic fallback.")

    @property
    def is_available(self) -> bool:
        return self.provider is not None

    # ─────────────────────────────────────────────────────────────────────
    # PUBLIC: compose() — for /v1/tick message generation
    # ─────────────────────────────────────────────────────────────────────

    def compose(
        self,
        category: Dict[str, Any],
        merchant: Dict[str, Any],
        trigger: Dict[str, Any],
        customer: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        LLM-powered message composition. Returns dict with body/cta/send_as/rationale
        or None if LLM is unavailable or fails (caller should fall back to deterministic).
        """
        if not self.is_available:
            return None

        # Cache key for determinism + rate limit protection
        cache_key = f"{merchant.get('merchant_id', '')}:{trigger.get('id', '')}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            user_prompt = self._build_compose_prompt(category, merchant, trigger, customer)
            raw = self._call_llm(SYSTEM_PROMPT, user_prompt, timeout=25)
            result = self._parse_json_response(raw)

            if result and "body" in result:
                # Post-validate
                result = self._post_validate(result, category, merchant, trigger, customer)
                self._cache[cache_key] = result
                return result

            logger.warning("LLM returned invalid compose response")
            return None

        except Exception as e:
            logger.warning(f"LLM compose failed: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────
    # PUBLIC: compose_reply() — for /v1/reply message generation
    # ─────────────────────────────────────────────────────────────────────

    def compose_reply(
        self,
        conversation: Dict[str, Any],
        inbound_message: str,
        from_role: str,
        merchant: Dict[str, Any],
        category: Dict[str, Any],
        customer_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        LLM-powered reply generation.
        Returns dict with action/body/cta/wait_seconds/rationale or None.
        """
        if not self.is_available:
            return None

        try:
            user_prompt = self._build_reply_prompt(
                conversation, inbound_message, from_role, merchant, category, customer_id
            )
            raw = self._call_llm(REPLY_SYSTEM_PROMPT, user_prompt, timeout=20)
            result = self._parse_json_response(raw)

            if result and "action" in result:
                # Ensure valid action
                if result["action"] not in ("send", "wait", "end"):
                    result["action"] = "send"
                return result

            return None

        except Exception as e:
            logger.warning(f"LLM reply failed: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────
    # PROMPT BUILDERS
    # ─────────────────────────────────────────────────────────────────────

    def _build_compose_prompt(
        self,
        category: Dict[str, Any],
        merchant: Dict[str, Any],
        trigger: Dict[str, Any],
        customer: Optional[Dict[str, Any]],
    ) -> str:
        """Builds a compact, highly focused prompt with only relevant context to minimize token usage."""
        cat_slug = category.get("slug", "unknown")
        voice = category.get("voice", {})
        taboos = voice.get("vocab_taboo", [])
        t_kind = trigger.get("kind", "")
        t_payload = trigger.get("payload", {})

        # Context relevance filtering (avoids blowing token budget)
        relevant_cat = {
            "slug": cat_slug,
            "tone": voice.get("tone", "peer_clinical" if cat_slug == "dentists" else "operator"),
            "taboos": taboos,
        }
        if "digest" in t_kind or "study" in str(t_payload).lower() or "research" in str(t_payload).lower():
            if category.get("digest"):
                relevant_cat["digest"] = category["digest"][:2]
        if "seasonal" in t_kind or "festival" in t_kind or "surge" in t_kind:
            if category.get("seasonal_beats"):
                relevant_cat["seasonal"] = category["seasonal_beats"][:2]
        if "trend" in t_kind:
            if category.get("trend_signals"):
                relevant_cat["trends"] = category["trend_signals"][:2]
        if customer and category.get("patient_content_library"):
            relevant_cat["content_library"] = category["patient_content_library"][:1]

        # Compact merchant info
        m_id = merchant.get("identity", {})
        m_perf = merchant.get("performance", {})
        m_sub = merchant.get("subscription", {})
        active_offers = [
            {"title": o.get("title"), "value": o.get("value")}
            for o in merchant.get("offers", []) if o.get("status") == "active"
        ]

        merchant_data = {
            "name": m_id.get("name", ""),
            "owner": m_id.get("owner_first_name", ""),
            "locality": m_id.get("locality", ""),
            "languages": m_id.get("languages", ["en"]),
            "subscription": {"status": m_sub.get("status"), "plan": m_sub.get("plan"), "days_remaining": m_sub.get("days_remaining"), "days_since_expiry": m_sub.get("days_since_expiry")},
            "perf_30d": {"views": m_perf.get("views", 0), "calls": m_perf.get("calls", 0), "ctr": m_perf.get("ctr", 0), "leads": m_perf.get("leads", 0)},
            "active_offers": active_offers,
            "signals": merchant.get("signals", [])[:5],
            "customer_agg": merchant.get("customer_aggregate", {}),
        }

        # Trigger data
        trigger_data = {
            "kind": t_kind,
            "scope": trigger.get("scope", "merchant"),
            "urgency": trigger.get("urgency", 3),
            "suppression_key": trigger.get("suppression_key", ""),
            "payload": t_payload,
        }

        # Customer data
        cust_data = None
        if customer:
            c_id = customer.get("identity", {})
            cust_data = {
                "name": c_id.get("name", ""),
                "lang": c_id.get("language_pref", "en"),
                "relation": customer.get("relationship", {}),
            }

        prompt = f"""COMPOSE VERA MESSAGE:
CATEGORY: {json.dumps(relevant_cat, separators=(',', ':'))}
MERCHANT: {json.dumps(merchant_data, separators=(',', ':'))}
TRIGGER: {json.dumps(trigger_data, separators=(',', ':'))}
CUSTOMER: {json.dumps(cust_data, separators=(',', ':')) if cust_data else "null (merchant-facing)"}

Follow all 5 scoring dimensions. Never fabricate unlisted numbers or offers."""
        return prompt

    def _build_reply_prompt(
        self,
        conversation: Dict[str, Any],
        inbound_message: str,
        from_role: str,
        merchant: Dict[str, Any],
        category: Dict[str, Any],
        customer_id: Optional[str],
    ) -> str:
        """Builds the user prompt for reply generation."""
        m_id = merchant.get("identity", {})
        cat_slug = category.get("slug", "unknown")
        turns = conversation.get("turns", [])
        initial_msg = conversation.get("initial_message", "")

        turns_text = ""
        for t in turns[-5:]:
            role = t.get("from", "unknown")
            msg = t.get("message", "")
            turns_text += f"  [{role}]: {msg}\n"

        prompt = f"""REPLY to this inbound message in a conversation:

MERCHANT: {m_id.get('name', 'Unknown')} ({cat_slug})
Owner: {m_id.get('owner_first_name', 'N/A')}
City: {m_id.get('city', '')}, Locality: {m_id.get('locality', '')}
Languages: {json.dumps(m_id.get('languages', ['en']))}
Active offers: {json.dumps([o.get('title') for o in merchant.get('offers', []) if o.get('status') == 'active'])}
Signals: {json.dumps(merchant.get('signals', []))}

INITIAL VERA MESSAGE: {initial_msg}

CONVERSATION HISTORY:
{turns_text if turns_text else '  (no prior turns)'}

INBOUND MESSAGE (from {from_role}): "{inbound_message}"
CUSTOMER ID: {customer_id or 'None (merchant is replying)'}

Respond with the appropriate action and message."""

        return prompt

    # ─────────────────────────────────────────────────────────────────────
    # LLM API CALLS
    # ─────────────────────────────────────────────────────────────────────

    def _call_llm(self, system_prompt: str, user_prompt: str, timeout: int = 25) -> str:
        """Routes to the correct provider."""
        if self.provider == "gemini":
            return self._call_gemini(system_prompt, user_prompt, timeout)
        elif self.provider == "groq":
            return self._call_groq(system_prompt, user_prompt, timeout)
        elif self.provider == "openai":
            return self._call_openai(system_prompt, user_prompt, timeout)
        raise ValueError(f"Unknown provider: {self.provider}")

    def _call_gemini(self, system: str, user: str, timeout: int) -> str:
        """Call Google Gemini API via REST."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"

        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 1024,
                "responseMimeType": "application/json",
            },
        }

        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        # Extract text from Gemini response
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")

        raise ValueError("Empty Gemini response")

    def _call_groq(self, system: str, user: str, timeout: int) -> str:
        """Call Groq API via REST (OpenAI-compatible)."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        primary_model = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
        models_to_try = [primary_model, "openai/gpt-oss-120b", "openai/gpt-oss-20b"]

        last_err = None
        for model in models_to_try:
            for attempt in range(2):
                try:
                    payload = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "temperature": 0,
                        "max_tokens": 2048,
                        "response_format": {"type": "json_object"},
                    }

                    resp = requests.post(
                        url,
                        json=payload,
                        headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                        timeout=timeout,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "")
                    elif resp.status_code == 429 and attempt == 0:
                        # Extract wait time or default to 3s
                        wait = 3.0
                        m = re.search(r"try again in ([0-9.]+)s", resp.text)
                        if m:
                            wait = min(float(m.group(1)) + 0.5, 6.0)
                        logger.info(f"Rate limited on {model}, sleeping {wait:.1f}s before retry")
                        time.sleep(wait)
                        continue
                    else:
                        last_err = f"{resp.status_code}: {resp.text}"
                        break
                except Exception as e:
                    last_err = str(e)
                    break

        raise ValueError(f"Groq API error: {last_err}")

    def _call_openai(self, system: str, user: str, timeout: int) -> str:
        """Call OpenAI-compatible API via REST."""
        url = f"{self.openai_base}/chat/completions"

        payload = {
            "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_tokens": 1024,
            "response_format": {"type": "json_object"},
        }

        resp = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")

        raise ValueError("Empty OpenAI response")

    # ─────────────────────────────────────────────────────────────────────
    # RESPONSE PARSING & VALIDATION
    # ─────────────────────────────────────────────────────────────────────

    def _parse_json_response(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response, handling edge cases."""
        if not raw_text:
            return None

        # Try direct parse first
        try:
            return json.loads(raw_text.strip())
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code blocks
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding first { ... } block
        match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"Could not parse LLM JSON: {raw_text[:200]}")
        return None

    def _post_validate(
        self,
        result: Dict[str, Any],
        category: Dict[str, Any],
        merchant: Dict[str, Any],
        trigger: Dict[str, Any],
        customer: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Post-validate and fix LLM output."""
        body = result.get("body", "")

        # 1. Check and fix CTA format
        valid_ctas = {"binary_yes_no", "choice", "open_ended", "none"}
        if result.get("cta") not in valid_ctas:
            result["cta"] = "open_ended"

        # 2. Check send_as
        scope = trigger.get("scope", "merchant")
        if customer or scope == "customer":
            result["send_as"] = "merchant_on_behalf"
        elif result.get("send_as") not in ("vera", "merchant_on_behalf"):
            result["send_as"] = "vera"

        # 3. Add suppression_key from trigger
        result["suppression_key"] = trigger.get("suppression_key", f"llm:{trigger.get('id', 'unknown')}")

        # 4. Add template fields
        result["template_name"] = None
        result["template_params"] = None

        # 5. Scrub category taboos from body
        voice = category.get("voice", {})
        taboos = voice.get("vocab_taboo", [])
        body_lower = body.lower()
        for taboo in taboos:
            clean = re.sub(r"\(.*?\)", "", taboo).strip().lower()
            if clean and clean in body_lower:
                # Replace with safe alternative
                body = re.sub(re.escape(clean), "clinically verified", body, flags=re.IGNORECASE)

        # 6. Scrub internal jargon (raw IDs like d_2026W17_... or trg_...)
        body = re.sub(r"\b[dmtc]_\d{4}[A-Za-z0-9_]+\b", "", body)
        body = re.sub(r" +", " ", body).strip()

        result["body"] = body

        # 7. Ensure rationale exists
        if not result.get("rationale"):
            result["rationale"] = f"LLM-composed message for {trigger.get('kind')} trigger targeting {merchant.get('merchant_id')}."

        return result


# Global singleton
llm_composer = LLMComposer()
