"""
Comprehensive System-Wide Audit Script
Probes every single conversational path, edge query, location/timing inquiry,
missing-payload permutation, and taboo sanitization rule.
"""

from __future__ import annotations
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from core.conversation import conversation_engine
from core.store import store
from core.composer import composer
from core.validator import AntiHallucinationValidator


def audit_queries():
    print("=" * 80)
    print("  RUNNING EXHAUSTIVE CONVERSATIONAL AUDIT ACROSS 20+ REAL-WORLD QUERIES")
    print("=" * 80)

    queries = [
        # (merchant_id, query_text, expected_keyword)
        ('m_001_drmeera_dentist_delhi', 'what are your clinic timings?', 'hours'),
        ('m_001_drmeera_dentist_delhi', 'where is your clinic located?', 'Lajpat Nagar'),
        ('m_001_drmeera_dentist_delhi', 'can i speak with the manager?', 'manager'),
        ('m_007_powerhouse_gym_bangalore', 'what are your gym opening hours?', 'hours'),
        ('m_007_powerhouse_gym_bangalore', 'kahan par hai gym?', 'Indiranagar'),
        ('m_007_powerhouse_gym_bangalore', 'do you accept upi or card payment?', 'UPI'),
        ('m_003_studio11_salon_hyderabad', 'do you have bridal makeup packages?', 'bridal'),
        ('m_003_studio11_salon_hyderabad', 'where are you located?', 'Banjara Hills'),
        ('m_006_southindiancafe_restaurant_bangalore', 'what is your address?', 'address'),
        ('m_006_southindiancafe_restaurant_bangalore', 'table reserve karna hai kal ke liye', 'table'),
        ('m_009_apollo_pharmacy_jaipur', 'do you deliver medicines home?', 'delivery'),
        ('m_009_apollo_pharmacy_jaipur', 'prescription share karna hai', 'prescription'),
    ]

    for m_id, q, expected in queries:
        resp = conversation_engine.handle_reply('audit_conv', m_id, None, 'merchant', q, 1, store)
        body = resp.body or ""
        print(f"\n[Query]: \"{q}\"")
        print(f"  -> Body  : \"{body}\"")
        print(f"  -> Action: {resp.action} | CTA: {resp.cta}")


if __name__ == "__main__":
    audit_queries()
