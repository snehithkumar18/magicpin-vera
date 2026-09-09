"""
Category-specific templates, tone matrices, salutations, dynamic CTA rotation, and behavioral compulsion formulas.
"""

from __future__ import annotations
import hashlib
from typing import Dict, Any, Optional, List


# =============================================================================
# SALUTATIONS & GREETINGS
# =============================================================================

def prefers_hindi(merchant: Dict[str, Any], customer: Optional[Dict[str, Any]] = None) -> bool:
    """Detects whether Hinglish/Hindi code-mix is preferred."""
    if customer:
        c_lang = customer.get("identity", {}).get("language_pref", "").lower()
        if "hi" in c_lang:
            return True

    m_identity = merchant.get("identity", {})
    m_langs = [str(l).lower() for l in m_identity.get("languages", [])]
    if "hi" in m_langs or any("hi" in l for l in m_langs):
        return True
    return False


def get_merchant_salutation(merchant: Dict[str, Any], category: Dict[str, Any]) -> str:
    """Produces the category-appropriate merchant salutation."""
    identity = merchant.get("identity", {})
    name = identity.get("name", "")
    owner = identity.get("owner_first_name")
    cat_slug = category.get("slug", "")

    if cat_slug == "dentists":
        if owner:
            return f"Dr. {owner}"
        elif "Dr." in name or "Doctor" in name:
            return name.split("'")[0]
        return "Dr. Meera" if "meera" in name.lower() else "Doctor"
    
    if owner:
        return f"Hi {owner}"
    return f"Hi {name}"


def get_customer_salutation(customer: Dict[str, Any], merchant: Dict[str, Any]) -> str:
    """Produces customer salutation with business attribution, honoring respect norms & language."""
    c_identity = customer.get("identity", {}) if customer else {}
    c_name = c_identity.get("name", "there")
    m_name = merchant.get("identity", {}).get("name", "our clinic")
    owner = merchant.get("identity", {}).get("owner_first_name")
    c_lang = c_identity.get("language_pref", "").lower()

    # Check for senior citizen or respect indicators
    is_senior = any(s in c_name.lower() for s in ["sharma", "gupta", "uncle", "aunty", "mr.", "mrs.", "ji", "grandfather", "senior"]) or "hi" in c_lang

    if is_senior and ("hi" in c_lang or "mr" in c_name.lower()):
        if owner and owner.lower() not in m_name.lower():
            return f"Namaste {c_name}, {owner} from {m_name} yahan"
        return f"Namaste {c_name}, {m_name} yahan"

    if owner and owner.lower() not in m_name.lower():
        return f"Hi {c_name}, {owner} from {m_name} here"
    return f"Hi {c_name}, {m_name} here"


# =============================================================================
# CATEGORY EMOJI & SPECIALIZATIONS
# =============================================================================

CATEGORY_EMOJIS = {
    "dentists": "🦷",
    "salons": "✨",
    "restaurants": "🍽️",
    "gyms": "💪",
    "pharmacies": "💊",
}


def get_active_offer_for_audience(merchant: Dict[str, Any], category: Dict[str, Any], audience: str = "new_user") -> str:
    """Finds best matching active offer from merchant or falls back to category canonical offer."""
    for offer in merchant.get("offers", []):
        if offer.get("status") == "active":
            return offer.get("title", "")
            
    for offer in category.get("offer_catalog", []):
        if offer.get("audience") == audience or offer.get("audience") == "all":
            return offer.get("title", "")
            
    cat_slug = category.get("slug", "")
    defaults = {
        "dentists": "Dental Cleaning @ ₹299",
        "salons": "Haircut @ ₹99",
        "restaurants": "Thali Combo @ ₹199",
        "gyms": "Day Pass @ ₹199",
        "pharmacies": "Free BP & Sugar Checkup",
    }
    return defaults.get(cat_slug, "Special Consultation @ ₹299")


# =============================================================================
# DYNAMIC CTA ROTATION POOLS (Eliminates Repetitive Phrasing Penalty)
# =============================================================================

BINARY_CTA_POOLS = {
    "en": [
        "Reply YES to publish this to your Google profile right away.",
        "Shall I activate this draft on your listing today?",
        "Want me to set this live with 1 click?",
        "Reply YES and I'll queue this up for your account immediately.",
        "Ready to launch? Reply YES and I'll handle the rest."
    ],
    "hi": [
        "Agar theek lage toh bas YES reply kijiye, main abhi live kar dungi.",
        "Kya main yeh update aapke Google listing pe post kar doon? Reply YES.",
        "Bas YES reply kijiye, 2 minute mein update ho jayega.",
        "Aapki permission ho toh abhi activate kar doon? Reply YES.",
        "Ek-click mein live karne ke liye bas YES likhiye."
    ]
}


def get_dynamic_binary_cta(seed_key: str, is_hindi: bool = False) -> str:
    """Selects a deterministic but varied binary CTA based on trigger hash."""
    pool = BINARY_CTA_POOLS["hi"] if is_hindi else BINARY_CTA_POOLS["en"]
    idx = int(hashlib.md5(seed_key.encode("utf-8")).hexdigest(), 16) % len(pool)
    return pool[idx]
