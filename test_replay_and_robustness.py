"""
Comprehensive Automated Test Suite for:
1. Unseen Payload Field Aliasing (Robustness)
2. Auto-Reply Hell Loop (Challenge Replay Scenario 1)
3. Compound Intent & Constraint Synthesis
4. Hostile / GST Out-of-Scope Guard (Challenge Replay Scenario 3)
"""

import json
from pathlib import Path
from bot import compose
from core.conversation import conversation_engine
from core.store import store


def test_unseen_payload_aliasing():
    print("\n--- 1. Testing Unseen Field Aliasing ---")
    root = Path("expanded")
    cat = json.load(open(root / "categories" / "dentists.json", encoding="utf-8"))
    m = json.load(open(root / "merchants" / "m_001_drmeera_dentist_delhi.json", encoding="utf-8"))
    
    # Mutated payload with completely different key names
    mutated_trigger = {
        "id": "trg_mutated_01",
        "scope": "merchant",
        "kind": "perf_dip",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "payload": {
            "metric_name": "patient_calls",
            "dropped_pct": -0.45,
            "baseline": 15
        },
        "urgency": 3,
        "suppression_key": "perf_dip:m001:mutated"
    }
    res = compose(cat, m, mutated_trigger)
    body = res.get("body", "")
    print(f"Composed body: {body}")
    assert "patient_calls" in body or "calls" in body, "Failed to capture aliased metric name"
    assert "45%" in body, "Failed to capture aliased dropped_pct"
    print("  [PASS] Successfully handled aliased/mutated field names.")


def test_auto_reply_hell():
    import uuid
    print("\n--- 2. Testing Auto-Reply Hell (Pattern B) ---")
    conv_id = f"test_conv_autoreply_{uuid.uuid4().hex[:6]}"
    m_id = "m_001_drmeera_dentist_delhi"
    auto_msg = "Thank you for contacting Dr. Meera's Dental Clinic. We are currently closed. Our hours are 9 AM to 8 PM."
    
    # Turn 1: First auto-reply
    res1 = conversation_engine.handle_reply(
        conversation_id=conv_id,
        merchant_id=m_id,
        customer_id=None,
        from_role="merchant",
        message=auto_msg,
        turn_number=1,
        context_store=store,
    )
    store.add_conversation_turn(conv_id, {
        "turn": 1,
        "from": "merchant",
        "message": auto_msg,
        "response_action": res1.action,
        "response_body": res1.body,
        "is_auto_reply": True
    })
    print(f"Turn 1 action: {res1.action} | body: {res1.body}")
    assert res1.action in ("wait", "send"), f"Expected wait or send on turn 1, got {res1.action}"
    if res1.action == "send" and res1.body:
        assert "2 minute" in res1.body or "takes just 2 minutes" in res1.body.lower(), "Expected Pattern B probe"

    # Turn 2: Repeated auto-reply
    res2 = conversation_engine.handle_reply(
        conversation_id=conv_id,
        merchant_id=m_id,
        customer_id=None,
        from_role="merchant",
        message=auto_msg,
        turn_number=2,
        context_store=store,
    )
    print(f"Turn 2 action: {res2.action} | body: {res2.body}")
    assert res2.action == "end", f"Expected end on turn 2, got {res2.action}"
    assert "owner" in res2.body.lower(), "Expected graceful exit mentioning owner"
    print("  [PASS] Auto-reply hell successfully resolved with Pattern B graceful exit.")


def test_compound_intent():
    print("\n--- 3. Testing Compound Intent (Affirmative + Price + Timing Constraints) ---")
    conv_id = "test_conv_compound_01"
    m_id = "m_001_drmeera_dentist_delhi"
    user_msg = "yes but only weekdays and ₹150"
    
    res = conversation_engine.handle_reply(
        conversation_id=conv_id,
        merchant_id=m_id,
        customer_id=None,
        from_role="merchant",
        message=user_msg,
        turn_number=1,
        context_store=store,
    )
    print(f"Compound Reply Body: {res.body}")
    assert "150" in res.body, "Failed to capture price constraint 150"
    assert "weekdays" in res.body.lower(), "Failed to capture timing constraint weekdays"
    assert res.cta == "binary_yes_no", "Expected binary CTA to confirm modified package"
    print("  [PASS] Compound intent synthesized both price and timing constraints without data loss.")


def test_gst_curveball():
    print("\n--- 4. Testing GST / Tax Curveball ---")
    conv_id = "test_conv_gst_01"
    m_id = "m_001_drmeera_dentist_delhi"
    user_msg = "Can you also help me file my GST?"
    
    res = conversation_engine.handle_reply(
        conversation_id=conv_id,
        merchant_id=m_id,
        customer_id=None,
        from_role="merchant",
        message=user_msg,
        turn_number=1,
        context_store=store,
    )
    print(f"GST Reply Body: {res.body}")
    assert "ca" in res.body.lower() or "accountant" in res.body.lower(), "Failed to redirect to CA/accountant"
    assert "magicpin" in res.body.lower() or "google business" in res.body.lower(), "Failed to clarify marketing focus"
    print("  [PASS] GST curveball properly handled with courteous scope boundary.")


if __name__ == "__main__":
    test_unseen_payload_aliasing()
    test_auto_reply_hell()
    test_compound_intent()
    test_gst_curveball()
    print("\n==================================================================")
    print("  ALL REPLAY & ROBUSTNESS TESTS PASSED WITH 100% COMPLIANCE!")
    print("==================================================================\n")
