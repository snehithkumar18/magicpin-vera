"""
Test specifically isolating the optional customer context:
Tests non-curious, fact-heavy triggers (e.g. competitor defense, festival, milestone, appointment)
when customer_id is None vs when customer is present.
"""

from __future__ import annotations
import json
from bot import compose

def test_missing_customer_behavior():
    print("=" * 80)
    print("  TESTING TRIGGER-DRIVEN COMPOSITION WITHOUT OPTIONAL CUSTOMER CONTEXT")
    print("=" * 80)

    category = {
        "slug": "dentists",
        "voice": {"salutation_merchant": "Dr. {name}", "vocab_taboo": ["completely cure", "guaranteed"]},
        "offer_catalog": [{"id": "off_clean", "title": "Dental Cleaning @ ₹299", "tier": "base"}]
    }

    merchant = {
        "merchant_id": "m_001_drmeera",
        "category_slug": "dentists",
        "identity": {"name": "Dr. Meera's Dental Clinic", "owner_first_name": "Meera", "locality": "Lajpat Nagar"},
        "performance": {"views": 2400, "ctr": 0.035},
        "offers": [{"id": "off_clean", "title": "Dental Cleaning @ ₹299", "status": "active"}]
    }

    # Case A: Competitor Opened (Merchant-facing, customer omitted)
    trigger_competitor = {
        "id": "trg_comp_001",
        "merchant_id": "m_001_drmeera",
        "kind": "competitor_opened",
        "payload": {"competitor_name": "Smile Studio", "distance_km": 1.3, "their_offer": "Dental Cleaning @ ₹199"}
    }
    out_a = compose(category, merchant, trigger_competitor, customer=None)
    print("\n[Case A: Competitor Opened | Customer = None]")
    print(f"  Send As  : {out_a['send_as']} (Expect: vera)")
    safe_a = out_a['body'].encode('ascii', 'ignore').decode('ascii')
    print(f"  Body     : \"{safe_a}\"")
    print(f"  Rationale: \"{out_a['rationale']}\"")
    assert out_a["send_as"] == "vera"
    assert "Smile Studio" in out_a["body"]
    assert "Dental Cleaning" in out_a["body"]
    assert "Lajpat Nagar" in out_a["body"]

    # Case B: Appointment Reminder with Customer Present vs Customer Omitted
    trigger_appt = {
        "id": "trg_appt_001",
        "merchant_id": "m_001_drmeera",
        "kind": "appointment_tomorrow",
        "payload": {"service": "Root Canal Consultation", "appointment_time": "tomorrow at 11:00 AM"}
    }
    customer = {
        "customer_id": "c_001_rahul",
        "merchant_id": "m_001_drmeera",
        "identity": {"name": "Rahul", "language_mix": "english"}
    }
    
    # B1: Customer Present
    out_b1 = compose(category, merchant, trigger_appt, customer=customer)
    print("\n[Case B1: Appointment Reminder | Customer = Rahul]")
    print(f"  Send As  : {out_b1['send_as']} (Expect: merchant_on_behalf)")
    safe_b1 = out_b1['body'].encode('ascii', 'ignore').decode('ascii')
    print(f"  Body     : \"{safe_b1}\"")
    assert out_b1["send_as"] == "merchant_on_behalf"
    assert "Rahul" in out_b1["body"]

    # B2: Customer Omitted (Fallback: Prompts merchant about upcoming schedule)
    out_b2 = compose(category, merchant, trigger_appt, customer=None)
    print("\n[Case B2: Appointment Reminder | Customer = None]")
    print(f"  Send As  : {out_b2['send_as']} (Expect: vera)")
    safe_b2 = out_b2['body'].encode('ascii', 'ignore').decode('ascii')
    print(f"  Body     : \"{safe_b2}\"")
    assert out_b2["send_as"] == "vera"

    print("\n" + "=" * 80)
    print("  CONFIRMED: Composer handles presence and absence of customer context gracefully.")
    print("=" * 80)

if __name__ == "__main__":
    test_missing_customer_behavior()
