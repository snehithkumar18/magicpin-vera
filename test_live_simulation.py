"""
Live Interactive Simulation & Grading Test for Vera Message Engine
Tests dynamic context injection, tick evaluations, auto-reply filters, and multi-turn replies.
"""

from __future__ import annotations
import json
import urllib.request
import time


SERVER_URL = "http://localhost:8080"


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title.upper()}")
    print("=" * 70)


def print_step(step: str, detail: str = ""):
    print(f"\n[*] [STEP] {step}")
    if detail:
        print(f"    {detail}")


def http_post(path: str, data: dict):
    req_body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{SERVER_URL}{path}",
        data=req_body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_get(path: str):
    req = urllib.request.Request(f"{SERVER_URL}{path}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_tests():
    print_banner("Running Live End-to-End Simulation Test on Vera Engine")

    # -------------------------------------------------------------------------
    # TEST 1: HEALTH & BASE METRICS
    # -------------------------------------------------------------------------
    print_step("Checking Server Liveness & Metadata", "GET /v1/healthz and /v1/metadata")
    health = http_get("/v1/healthz")
    metadata = http_get("/v1/metadata")
    print(f"   Status: {health.get('status')} | Loaded Contexts: {health.get('contexts_loaded')}")
    print(f"   Model: {metadata.get('model')} | Approach: {metadata.get('approach')[:50]}...")
    assert health.get("status") == "ok", "Server not healthy"

    # -------------------------------------------------------------------------
    # TEST 2: DYNAMIC CONTEXT INJECTION (Brand New Merchant & Research Paper)
    # -------------------------------------------------------------------------
    print_step("Injecting BRAND NEW Unseen Context", "POST /v1/context (Simulating Judge Live Injection)")
    
    # 1. New Merchant
    new_merchant = {
        "merchant_id": "m_unseen_ananya_dentist_mumbai",
        "category_slug": "dentists",
        "identity": {
            "name": "Dr. Ananya's Smile Clinic",
            "city": "Mumbai",
            "locality": "Bandra West",
            "owner_first_name": "Ananya"
        },
        "performance": {"views": 3850, "calls": 42, "ctr": 0.038},
        "offers": [{"id": "o_ananya_01", "title": "Teeth Whitening @ ₹1,499", "status": "active"}]
    }
    resp_m = http_post("/v1/context", {
        "scope": "merchant",
        "context_id": "m_unseen_ananya_dentist_mumbai",
        "version": 1,
        "payload": new_merchant
    })
    print(f"   Merchant Ingestion: Accepted = {resp_m.get('accepted')} (Ack: {resp_m.get('ack_id')})")

    # 2. New Unseen Research Trigger
    unseen_trigger = {
        "id": "trg_unseen_laser_whitening_2026",
        "scope": "merchant",
        "kind": "research_digest",
        "merchant_id": "m_unseen_ananya_dentist_mumbai",
        "payload": {
            "top_item_id": "d_unseen_laser_study"
        },
        "suppression_key": "research:dentists:laser:2026-W18"
    }
    # Also push the research item into category digest
    cat_dentists = http_get("/v1/healthz") # verify
    unseen_category_update = {
        "slug": "dentists",
        "voice": {"tone": "peer_clinical", "vocab_taboo": ["completely cure", "guaranteed"]},
        "offer_catalog": [{"id": "den_003", "title": "Teeth Whitening @ ₹1,499", "value": "1499", "audience": "all"}],
        "digest": [
            {
                "id": "d_unseen_laser_study",
                "title": "diode laser activation increases shade retention by 44%",
                "source": "Journal of Esthetic Dentistry May 2026, p.88",
                "trial_n": 3400,
                "patient_segment": "cosmetic whitening"
            }
        ]
    }
    http_post("/v1/context", {
        "scope": "category",
        "context_id": "dentists",
        "version": 2,  # Atomic version upgrade
        "payload": unseen_category_update
    })
    http_post("/v1/context", {
        "scope": "trigger",
        "context_id": "trg_unseen_laser_whitening_2026",
        "version": 1,
        "payload": unseen_trigger
    })

    # -------------------------------------------------------------------------
    # TEST 3: TICK EVALUATION (Trigger Fire)
    # -------------------------------------------------------------------------
    print_step("Simulated Clock Wakeup", "POST /v1/tick with unseen trigger")
    tick_resp = http_post("/v1/tick", {
        "now": "2026-05-01T10:00:00Z",
        "available_triggers": ["trg_unseen_laser_whitening_2026"]
    })
    
    actions = tick_resp.get("actions", [])
    assert len(actions) > 0, "No action returned on tick"
    action = actions[0]
    conv_id = action.get("conversation_id")
    
    print("\n   [COMPOSED OUTBOUND MESSAGE TO DR. ANANYA]:")
    safe_outbound = str(action.get('body', '')).encode('ascii', 'ignore').decode('ascii')
    print(f"   \"{safe_outbound}\"")
    print(f"   CTA: {action.get('cta')} | Send As: {action.get('send_as')}")
    print(f"   Rationale: {action.get('rationale')}")

    # Check grounding
    assert "Dr. Ananya" in action.get("body"), "Failed to extract owner salutation"
    assert "3,400" in action.get("body"), "Failed to extract dynamic trial sample size"
    assert "May 2026, p.88" in action.get("body"), "Failed to extract citation"

    # -------------------------------------------------------------------------
    # TEST 4: MULTI-TURN AUTO-REPLY FILTERING
    # -------------------------------------------------------------------------
    print_step("Testing WhatsApp Business Auto-Reply Filter", "POST /v1/reply with canned greeting")
    canned_reply = "Thank you for messaging Dr. Ananya's Smile Clinic! We are currently busy with patients and will reply shortly."
    reply_resp = http_post("/v1/reply", {
        "conversation_id": conv_id,
        "merchant_id": "m_unseen_ananya_dentist_mumbai",
        "from_role": "merchant",
        "message": canned_reply,
        "turn_number": 2
    })
    print(f"   Server Action: {reply_resp.get('action')} (Wait Seconds: {reply_resp.get('wait_seconds')})")
    print(f"   Rationale: {reply_resp.get('rationale')}")
    assert reply_resp.get("action") == "wait", "Auto-reply was not filtered!"

    # -------------------------------------------------------------------------
    # TEST 5: INSTANT INTENT HANDOFF
    # -------------------------------------------------------------------------
    print_step("Testing Instant Intent Handoff", "POST /v1/reply with merchant saying 'Yes please send it'")
    affirmative_reply = "Yes please send it, focus on whitening"
    reply_yes = http_post("/v1/reply", {
        "conversation_id": conv_id,
        "merchant_id": "m_unseen_ananya_dentist_mumbai",
        "from_role": "merchant",
        "message": affirmative_reply,
        "turn_number": 3
    })
    print(f"   Server Action: {reply_yes.get('action')}")
    safe_body = str(reply_yes.get('body', '')).encode('ascii', 'ignore').decode('ascii')
    print(f"   Delivered Response: \"{safe_body}\"")
    print(f"   Rationale: {reply_yes.get('rationale')}")
    assert reply_yes.get("action") == "send", "Failed to execute affirmative intent"

    print_banner("All 5 Live Simulation Tests Passed Flawlessly (100% Score)!")


if __name__ == "__main__":
    run_tests()
