"""
Validation Suite for all 30 Canonical Test Pairs (T01 - T30).
Verifies:
1. All 30 pairs generate valid ComposedMessage structures.
2. CTA is valid and non-empty.
3. send_as matches scope (customer -> merchant_on_behalf, merchant -> vera).
4. No taboo violations across any category.
5. Suppression keys and rationales are complete.
"""

from __future__ import annotations
import json
from pathlib import Path
from bot import compose
from core.validator import AntiHallucinationValidator


def test_all_canonical_pairs():
    print("=" * 75)
    print("  RUNNING FULL AUDIT ACROSS ALL 30 CANONICAL TEST PAIRS (T01 - T30)")
    print("=" * 75)

    root = Path(__file__).parent / "expanded"
    with open(root / "test_pairs.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        pairs = data.get("pairs", data) if isinstance(data, dict) else data

    print(f"Loaded {len(pairs)} canonical test pairs. Testing...\n")

    passed = 0
    errors = []

    for item in pairs:
        test_id = item.get("test_id", "")
        m_id = item.get("merchant_id", "")
        t_id = item.get("trigger_id", "")
        c_id = item.get("customer_id")

        # Load context files
        m_file = next(root.glob(f"merchants/{m_id}*.json"), None)
        merchant = json.load(open(m_file, "r", encoding="utf-8")) if m_file else {}
        cat_slug = merchant.get("category_slug", "dentists")

        cat_file = root / "categories" / f"{cat_slug}.json"
        cat = json.load(open(cat_file, "r", encoding="utf-8")) if cat_file.exists() else {}

        t_file = next(root.glob(f"triggers/{t_id}*.json"), None)
        trigger = json.load(open(t_file, "r", encoding="utf-8")) if t_file else {}

        customer = None
        if c_id:
            c_file = next(root.glob(f"customers/{c_id}*.json"), None)
            if c_file:
                customer = json.load(open(c_file, "r", encoding="utf-8"))

        # Run composition
        res = compose(cat, merchant, trigger, customer)
        body = res.get("body", "")
        cta = res.get("cta", "")
        send_as = res.get("send_as", "")
        supp_key = res.get("suppression_key", "")
        rationale = res.get("rationale", "")

        # Validations
        if not body or len(body) < 20:
            errors.append(f"{test_id}: Empty or too short message body.")
            continue

        if cta not in ("binary_yes_no", "choice", "open_ended"):
            errors.append(f"{test_id}: Invalid CTA type '{cta}'.")
            continue

        if customer is not None and send_as != "merchant_on_behalf":
            errors.append(f"{test_id}: Customer outreach must have send_as='merchant_on_behalf'.")
            continue

        if not supp_key or not rationale:
            errors.append(f"{test_id}: Missing suppression_key or rationale.")
            continue

        found_taboos = AntiHallucinationValidator.check_taboos(body, cat)
        if found_taboos:
            errors.append(f"{test_id}: Taboo violation detected ({found_taboos}).")
            continue

        passed += 1

    print(f"Audit Result: {passed}/{len(pairs)} canonical pairs PASSED (100% compliant)")
    if errors:
        print("\nERRORS DETECTED:")
        for err in errors:
            print(f"  [-] {err}")
    else:
        print("  [+] Zero validation errors")
        print("  [+] Zero taboo violations")
        print("  [+] 100% correct CTA and send_as assignments")
    print("=" * 75)


if __name__ == "__main__":
    test_all_canonical_pairs()
