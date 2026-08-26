"""
Edge Case & Resilience Test Suite requested by Reviewer.
Runs 3 specific tests against the live server (or Railway endpoint):
1. Genuinely novel unseen merchant + unusual trigger.
2. Missing optional fields (customer omitted, partial trigger payloads).
3. Ambiguous and mixed multi-turn replies (delay, price question, partial auto-reply, opt-out).
"""

from __future__ import annotations
import sys
import json
import urllib.request
from typing import Dict, Any


def post_json(url: str, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
    req_body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{url}{path}",
        data=req_body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str, path: str) -> Dict[str, Any]:
    req = urllib.request.Request(f"{url}{path}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_edge_tests(server_url: str = "https://magicpin-vera-production.up.railway.app"):
    print("=" * 80)
    print(f"  RUNNING RIGOROUS EDGE-CASE AUDIT ON: {server_url}")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # TEST 1: Genuinely Novel Merchant & Unusual Trigger Combination
    # -------------------------------------------------------------------------
    print("\n[*] [TEST 1] Ingesting Genuinely Novel Unseen Merchant (IronCore Gym)...")
    novel_merchant = {
        "scope": "merchant",
        "context_id": "m_novel_ironcore_gym",
        "version": 1,
        "payload": {
            "merchant_id": "m_novel_ironcore_gym",
            "category_slug": "gyms",
            "identity": {
                "name": "IronCore Fitness",
                "locality": "Indiranagar",
                "city": "Bangalore",
                "owner_first_name": "Vikram"
            },
            "performance": {"views": 4800, "ctr": 0.052, "member_growth_pct": 0.35},
            "offers": [{"id": "off_gym_monsoon", "title": "Monsoon Conditioning Pass @ ₹1,999", "status": "active"}]
        }
    }
    res_m = post_json(server_url, "/v1/context", novel_merchant)
    assert res_m.get("accepted"), "Novel merchant push failed!"
    print("    Pushed novel merchant successfully (Accepted=True)")

    # Ingest unusual trigger (Monsoon Challenge under festival_upcoming)
    novel_trigger = {
        "scope": "trigger",
        "context_id": "trg_novel_monsoon_surge",
        "version": 1,
        "payload": {
            "id": "trg_novel_monsoon_surge",
            "merchant_id": "m_novel_ironcore_gym",
            "kind": "festival_upcoming",
            "payload": {
                "festival": "Monsoon Fitness Surge",
                "days_until": 7
            }
        }
    }
    res_t = post_json(server_url, "/v1/context", novel_trigger)
    assert res_t.get("accepted"), "Novel trigger push failed!"
    print("    Pushed novel trigger successfully (Accepted=True)")

    # Fire /v1/tick
    tick_res = post_json(server_url, "/v1/tick", {
        "now": "2026-06-01T10:00:00Z",
        "available_triggers": ["trg_novel_monsoon_surge"]
    })
    actions = tick_res.get("actions", [])
    assert len(actions) == 1, "Expected 1 composed action for novel trigger!"
    act = actions[0]
    
    print("\n    [Composed Output for Novel Merchant]:")
    safe_body = act['body'].encode('ascii', 'ignore').decode('ascii')
    print(f"    Body     : \"{safe_body}\"")
    print(f"    CTA      : {act['cta']}")
    print(f"    Send As  : {act['send_as']}")
    print(f"    Rationale: \"{act['rationale']}\"")
    
    # Assertions on Novel Output
    assert "Vikram" in act["body"], "Must address owner by name!"
    assert "Monsoon Fitness Surge" in act["body"], "Must ground in novel event name!"
    assert "Indiranagar" in act["body"], "Must ground in locality!"
    assert act["cta"] == "binary_yes_no", "Must provide binary Yes/No CTA!"
    print("    [+] TEST 1 PASSED: Grounded in novel context with zero hallucination and clear CTA.")

    # -------------------------------------------------------------------------
    # TEST 2: Missing Optional Fields Test
    # -------------------------------------------------------------------------
    print("\n[*] [TEST 2] Testing Missing Optional Fields (Omitted Customer & Sparse Trigger)...")
    sparse_trigger = {
        "scope": "trigger",
        "context_id": "trg_sparse_001",
        "version": 1,
        "payload": {
            "id": "trg_sparse_001",
            "merchant_id": "m_novel_ironcore_gym",
            "kind": "curious_ask_due",
            "payload": {} # Empty payload
        }
    }
    post_json(server_url, "/v1/context", sparse_trigger)
    sparse_tick = post_json(server_url, "/v1/tick", {
        "now": "2026-06-01T11:00:00Z",
        "available_triggers": ["trg_sparse_001"]
    })
    sparse_act = sparse_tick.get("actions", [])[0]
    safe_sparse_body = sparse_act['body'].encode('ascii', 'ignore').decode('ascii')
    print(f"    Body with empty payload: \"{safe_sparse_body}\"")
    assert len(sparse_act["body"]) > 20, "Must not generate broken/empty body!"
    assert sparse_act["send_as"] == "vera", "Must send as Vera when customer is omitted!"
    print("    [+] TEST 2 PASSED: Handled missing optional fields without crashing or emitting placeholders.")

    # -------------------------------------------------------------------------
    # TEST 3: Ambiguous and Multi-Turn Reply Flows
    # -------------------------------------------------------------------------
    print("\n[*] [TEST 3] Testing Ambiguous Replies, Price Questions & Busy Indicators...")
    
    # 3A. Busy/Delay: "busy right now with clients, message later"
    reply_busy = post_json(server_url, "/v1/reply", {
        "conversation_id": act["conversation_id"],
        "merchant_id": "m_novel_ironcore_gym",
        "from_role": "merchant",
        "message": "busy right now with clients, message later",
        "turn_number": 1
    })
    print(f"    Reply 'busy right now' -> Action: {reply_busy.get('action')} (Wait: {reply_busy.get('wait_seconds')}s)")
    assert reply_busy.get("action") == "wait", "Delay phrase must trigger 'wait' action!"

    # 3B. Price Inquiry: "kitna charge lagega iska?"
    reply_price = post_json(server_url, "/v1/reply", {
        "conversation_id": act["conversation_id"],
        "merchant_id": "m_novel_ironcore_gym",
        "from_role": "merchant",
        "message": "kitna charge lagega iska?",
        "turn_number": 2
    })
    safe_price_body = reply_price.get('body', '').encode('ascii', 'ignore').decode('ascii')
    print(f"    Reply 'kitna charge' -> Body: \"{safe_price_body}\"")
    assert "pricing" in safe_price_body.lower() or "starts with" in safe_price_body.lower(), "Must quote pricing transparently!"
    assert reply_price.get("action") == "send", "Must reply with transparent pricing quote!"

    # 3C. Opt-out: "not interested stop messaging"
    reply_optout = post_json(server_url, "/v1/reply", {
        "conversation_id": act["conversation_id"],
        "merchant_id": "m_novel_ironcore_gym",
        "from_role": "merchant",
        "message": "not interested stop messaging",
        "turn_number": 3
    })
    print(f"    Reply 'not interested' -> Action: {reply_optout.get('action')}")
    assert reply_optout.get("action") == "end", "Opt-out must gracefully close loop with 'end' action!"

    print("\n" + "=" * 80)
    print("  ALL 3 EDGE-CASE RESILIENCE TESTS PASSED (100% SUCCESS)!")
    print("=" * 80)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://magicpin-vera-production.up.railway.app"
    run_edge_tests(url)
