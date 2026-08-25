"""
Data models for magicpin Vera Message Engine.
Covers Category, Merchant, Customer, and Trigger contexts along with composed output representations.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


# =============================================================================
# CONTEXT MODELS
# =============================================================================

@dataclass
class VoiceProfile:
    tone: str = "peer_clinical"
    register: str = "respectful_collegial"
    code_mix: str = "hindi_english_natural"
    vocab_allowed: List[str] = field(default_factory=list)
    vocab_taboo: List[str] = field(default_factory=list)
    salutation_examples: List[str] = field(default_factory=list)
    tone_examples: List[str] = field(default_factory=list)


@dataclass
class OfferTemplate:
    id: str = ""
    title: str = ""
    value: str = ""
    audience: str = "all"
    type: str = "service_at_price"


@dataclass
class DigestItem:
    id: str = ""
    kind: str = "research"
    title: str = ""
    source: str = ""
    trial_n: Optional[int] = None
    patient_segment: Optional[str] = None
    summary: str = ""


@dataclass
class CategoryContext:
    slug: str
    display_name: str = ""
    voice: VoiceProfile = field(default_factory=VoiceProfile)
    offer_catalog: List[OfferTemplate] = field(default_factory=list)
    peer_stats: Dict[str, Any] = field(default_factory=dict)
    digest: List[DigestItem] = field(default_factory=list)
    patient_content_library: List[Dict[str, Any]] = field(default_factory=list)
    seasonal_beats: List[Dict[str, Any]] = field(default_factory=list)
    trend_signals: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MerchantIdentity:
    name: str = ""
    city: str = ""
    locality: str = ""
    place_id: str = ""
    verified: bool = False
    languages: List[str] = field(default_factory=lambda: ["en"])
    owner_first_name: Optional[str] = None
    established_year: Optional[int] = None


@dataclass
class PerformanceSnapshot:
    window_days: int = 30
    views: int = 0
    calls: int = 0
    directions: int = 0
    ctr: float = 0.0
    leads: int = 0
    delta_7d: Dict[str, float] = field(default_factory=dict)


@dataclass
class MerchantOffer:
    id: str = ""
    title: str = ""
    status: str = "active"
    started: Optional[str] = None
    ended: Optional[str] = None


@dataclass
class MerchantContext:
    merchant_id: str
    category_slug: str
    identity: MerchantIdentity = field(default_factory=MerchantIdentity)
    subscription: Dict[str, Any] = field(default_factory=dict)
    performance: PerformanceSnapshot = field(default_factory=PerformanceSnapshot)
    offers: List[MerchantOffer] = field(default_factory=list)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    customer_aggregate: Dict[str, Any] = field(default_factory=dict)
    signals: List[str] = field(default_factory=list)


@dataclass
class CustomerIdentity:
    name: str = ""
    phone_redacted: str = ""
    language_pref: str = "en"
    age_band: Optional[str] = None


@dataclass
class CustomerRelationship:
    first_visit: Optional[str] = None
    last_visit: Optional[str] = None
    visits_total: int = 0
    services_received: List[str] = field(default_factory=list)
    lifetime_value: Optional[float] = None


@dataclass
class CustomerContext:
    customer_id: str
    merchant_id: str
    identity: CustomerIdentity = field(default_factory=CustomerIdentity)
    relationship: CustomerRelationship = field(default_factory=CustomerRelationship)
    state: str = "active"
    preferences: Dict[str, Any] = field(default_factory=dict)
    consent: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggerContext:
    id: str
    scope: Literal["merchant", "customer"] = "merchant"
    kind: str = "general"
    source: Literal["external", "internal"] = "external"
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    urgency: int = 3
    suppression_key: str = ""
    expires_at: Optional[str] = None


# =============================================================================
# COMPOSE & ACTION OUTPUT MODELS
# =============================================================================

class ComposedMessage(BaseModel):
    body: str = Field(..., description="WhatsApp message body text")
    cta: str = Field(..., description="Call-to-action classification (binary_yes_no, choice, open_ended, none)")
    send_as: Literal["vera", "merchant_on_behalf"] = Field(..., description="Sender identity")
    suppression_key: str = Field(..., description="Suppression/dedup key")
    rationale: str = Field(..., description="Reasoning and strategic intent behind this message")
    template_name: Optional[str] = Field(default=None, description="Pre-approved WhatsApp template name if first outbound")
    template_params: Optional[List[str]] = Field(default=None, description="Template variable substitution parameters")


class TickAction(BaseModel):
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    send_as: Literal["vera", "merchant_on_behalf"]
    trigger_id: str
    template_name: Optional[str] = None
    template_params: Optional[List[str]] = None
    body: str
    cta: str
    suppression_key: str
    rationale: str


class ReplyActionResponse(BaseModel):
    action: Literal["send", "wait", "end"]
    body: Optional[str] = None
    cta: Optional[str] = None
    wait_seconds: Optional[int] = None
    rationale: str
