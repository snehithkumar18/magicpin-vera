"""
magicpin Vera — Payload Normalization & Dynamic Schema Aliasing Layer.
Maps all incoming synonym keys, nested payloads, and variations to canonical schemas
so the engine never degrades to generic fallbacks on unseen judge injections.
"""

from __future__ import annotations
import re
from typing import Dict, Any, Optional, List, Tuple


class PayloadNormalizer:
    """Normalizes and extracts ground truth fields from dynamic payloads."""

    SYNONYM_MAP = {
        "metric": [
            "metric", "metric_name", "dropped_metric", "metric_dropped",
            "kpi", "performance_metric", "stat_name", "tracking_metric"
        ],
        "delta_pct": [
            "delta_pct", "percentage_drop", "drop_pct", "dropped_pct",
            "spike_pct", "change_pct", "pct_change", "percentage_change", "growth_pct"
        ],
        "baseline": [
            "vs_baseline", "baseline", "average", "weekly_avg", "normal_volume", "typical"
        ],
        "title": [
            "title", "paper_title", "headline", "topic_title", "paper_summary",
            "digest_summary", "article_title", "finding"
        ],
        "source": [
            "source", "publication", "journal", "authority", "circular", "reference"
        ],
        "trial_n": [
            "trial_n", "sample_size", "n_patients", "patient_count", "cohort_size", "participants"
        ],
        "patient_segment": [
            "patient_segment", "target_cohort", "segment", "audience_group", "demographic"
        ],
        "service": [
            "service", "service_name", "treatment", "service_due", "treatment_type",
            "package_name", "procedure"
        ],
        "available_slots": [
            "available_slots", "slots", "open_slots", "times", "timings", "preferred_slots"
        ],
        "competitor_name": [
            "competitor_name", "competitor", "business_name", "new_clinic", "new_salon",
            "new_restaurant", "new_gym", "new_pharmacy", "comp_name"
        ],
        "distance_km": [
            "distance_km", "distance", "distance_in_km", "dist_km", "proximity"
        ],
        "their_offer": [
            "their_offer", "competitor_offer", "promo", "discount_offered", "comp_deal"
        ],
        "festival": [
            "festival", "festival_name", "event_name", "season_event", "holiday", "occasion"
        ],
        "days_until": [
            "days_until", "days_left", "countdown_days", "in_days"
        ],
        "molecule": [
            "molecule", "medicine", "drug", "drug_name", "molecule_name", "item_name", "product"
        ],
        "affected_batches": [
            "affected_batches", "batches", "batch_numbers", "lot_numbers", "recalled_batches"
        ],
        "manufacturer": [
            "manufacturer", "mfr", "pharma_company", "brand", "maker"
        ],
        "intent_topic": [
            "intent_topic", "topic", "planning_goal", "feature_request", "campaign_type"
        ],
        "deadline_iso": [
            "deadline_iso", "deadline", "compliance_deadline", "due_date", "valid_until"
        ],
        "estimated_uplift_pct": [
            "estimated_uplift_pct", "uplift_pct", "expected_growth", "views_uplift", "gain_pct"
        ],
    }

    @classmethod
    def normalize_payload(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flattens and canonicalizes payload keys.
        Supports both direct keys and nested dictionary structures.
        """
        if not isinstance(payload, dict):
            return {}

        normalized: Dict[str, Any] = dict(payload)

        # Look for nested containers commonly sent by judges (e.g., top_item, data, alert)
        for sub_key in ("top_item", "data", "alert", "details", "item"):
            if isinstance(payload.get(sub_key), dict):
                for k, v in payload[sub_key].items():
                    if k not in normalized:
                        normalized[k] = v

        # Map synonyms to canonical names
        for canonical, synonyms in cls.SYNONYM_MAP.items():
            if canonical not in normalized or normalized[canonical] is None:
                for syn in synonyms:
                    if syn in payload and payload[syn] is not None:
                        normalized[canonical] = payload[syn]
                        break
                    # Also check nested containers
                    for sub_key in ("top_item", "data", "alert", "details", "item"):
                        sub_dict = payload.get(sub_key)
                        if isinstance(sub_dict, dict) and syn in sub_dict and sub_dict[syn] is not None:
                            normalized[canonical] = sub_dict[syn]
                            break
                    if canonical in normalized:
                        break

        return normalized

    @classmethod
    def extract_digest_item(cls, category: Dict[str, Any], top_item_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Finds the matching digest item from CategoryContext, or the latest injected research item.
        """
        digest_list = category.get("digest", [])
        if not digest_list:
            return None

        if top_item_id:
            for item in digest_list:
                if item.get("id") == top_item_id:
                    return item

        # If top_item_id not found or not provided, return the most recent research/compliance item
        return digest_list[0] if digest_list else None
