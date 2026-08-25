"""
Automated unit & integration test suite for magicpin Vera API Server.
"""

import unittest
import json
from pathlib import Path
from fastapi.testclient import TestClient
from server import app
from core.store import store


class TestVeraServer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_01_metadata(self):
        resp = self.client.get("/v1/metadata")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("team_name", data)
        self.assertIn("model", data)
        self.assertEqual(data["version"], "1.0.0")

    def test_02_healthz_and_context_push(self):
        # Push category
        cat_payload = {
            "slug": "dentists",
            "display_name": "Dentists",
            "voice": {"tone": "peer_clinical", "vocab_taboo": ["completely cure"]},
            "offer_catalog": [{"id": "den_001", "title": "Dental Cleaning @ ₹299", "value": "299", "audience": "new_user"}],
            "digest": [{"id": "d_test_01", "title": "Fluoride Study", "source": "JIDA Oct 2026, p.14", "trial_n": 2100}],
        }
        resp = self.client.post("/v1/context", json={
            "scope": "category",
            "context_id": "dentists",
            "version": 1,
            "payload": cat_payload,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["accepted"])

        # Push merchant
        m_payload = {
            "merchant_id": "m_test_001",
            "category_slug": "dentists",
            "identity": {"name": "Dr. Meera's Dental Clinic", "city": "Delhi", "locality": "Lajpat Nagar", "owner_first_name": "Meera"},
            "performance": {"views": 2410, "calls": 18, "ctr": 0.021},
            "offers": [{"id": "o_001", "title": "Dental Cleaning @ ₹299", "status": "active"}],
        }
        resp = self.client.post("/v1/context", json={
            "scope": "merchant",
            "context_id": "m_test_001",
            "version": 1,
            "payload": m_payload,
        })
        self.assertEqual(resp.status_code, 200)

        # Check stale version conflict (409)
        resp_stale = self.client.post("/v1/context", json={
            "scope": "merchant",
            "context_id": "m_test_001",
            "version": 0,
            "payload": m_payload,
        })
        self.assertEqual(resp_stale.status_code, 409)
        self.assertFalse(resp_stale.json()["accepted"])

        # Check Healthz
        resp_health = self.client.get("/v1/healthz")
        self.assertEqual(resp_health.status_code, 200)
        counts = resp_health.json()["contexts_loaded"]
        self.assertGreaterEqual(counts["category"], 1)
        self.assertGreaterEqual(counts["merchant"], 1)

    def test_03_tick_and_action(self):
        # Push a test trigger
        t_payload = {
            "id": "trg_test_001",
            "scope": "merchant",
            "kind": "research_digest",
            "merchant_id": "m_test_001",
            "payload": {"top_item_id": "d_test_01"},
            "suppression_key": "test:suppress:001",
        }
        self.client.post("/v1/context", json={
            "scope": "trigger",
            "context_id": "trg_test_001",
            "version": 1,
            "payload": t_payload,
        })

        resp_tick = self.client.post("/v1/tick", json={
            "now": "2026-04-26T10:30:00Z",
            "available_triggers": ["trg_test_001"],
        })
        self.assertEqual(resp_tick.status_code, 200)
        actions = resp_tick.json()["actions"]
        self.assertEqual(len(actions), 1)
        act = actions[0]
        self.assertEqual(act["send_as"], "vera")
        self.assertEqual(act["cta"], "binary_yes_no")
        self.assertIn("Dr. Meera", act["body"])
        self.assertIn("JIDA Oct 2026, p.14", act["body"])

    def test_04_reply_handling(self):
        # 1. WhatsApp Auto-Reply Detection
        resp_auto = self.client.post("/v1/reply", json={
            "conversation_id": "conv_test_001",
            "merchant_id": "m_test_001",
            "message": "Thank you for contacting Dr. Meera's Clinic! We will reply shortly.",
            "turn_number": 2,
        })
        self.assertEqual(resp_auto.status_code, 200)
        self.assertEqual(resp_auto.json()["action"], "wait")
        self.assertIn("automated", resp_auto.json()["rationale"].lower())

        # 2. Affirmation / Intent Handoff
        resp_yes = self.client.post("/v1/reply", json={
            "conversation_id": "conv_test_001",
            "merchant_id": "m_test_001",
            "message": "Yes please send it",
            "turn_number": 3,
        })
        self.assertEqual(resp_yes.status_code, 200)
        self.assertEqual(resp_yes.json()["action"], "send")
        self.assertIn("Done", resp_yes.json()["body"])

        # 3. Opt-out
        resp_no = self.client.post("/v1/reply", json={
            "conversation_id": "conv_test_001",
            "merchant_id": "m_test_001",
            "message": "Not interested stop",
            "turn_number": 4,
        })
        self.assertEqual(resp_no.status_code, 200)
        self.assertEqual(resp_no.json()["action"], "end")


if __name__ == "__main__":
    unittest.main()
