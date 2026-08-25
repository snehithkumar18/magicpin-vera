"""
Batch generator for creating the official 30-item submission.jsonl file.
Iterates over canonical test pairs in expanded/test_pairs.json.
"""

from __future__ import annotations
import json
from pathlib import Path
from bot import compose


def main():
    root = Path(__file__).parent
    expanded = root / "expanded"
    test_pairs_file = expanded / "test_pairs.json"
    
    if not test_pairs_file.exists():
        print(f"Error: {test_pairs_file} not found. Run dataset/generate_dataset.py first.")
        return

    with open(test_pairs_file, "r", encoding="utf-8") as f:
        pairs_data = json.load(f)

    test_pairs = pairs_data.get("pairs", [])
    print(f"Loaded {len(test_pairs)} canonical test pairs. Generating messages...")

    out_file = root / "submission.jsonl"
    lines = []

    for pair in test_pairs:
        test_id = pair["test_id"]
        t_id = pair["trigger_id"]
        m_id = pair["merchant_id"]
        c_id = pair.get("customer_id")

        # Load Merchant
        m_path = expanded / "merchants" / f"{m_id}.json"
        if not m_path.exists():
            # Try searching glob if filename has extra suffix
            m_matches = list((expanded / "merchants").glob(f"{m_id}*.json"))
            if m_matches:
                m_path = m_matches[0]
        
        merchant = json.load(open(m_path, "r", encoding="utf-8"))
        cat_slug = merchant.get("category_slug", "dentists")

        # Load Category
        cat_path = expanded / "categories" / f"{cat_slug}.json"
        category = json.load(open(cat_path, "r", encoding="utf-8"))

        # Load Trigger
        t_path = expanded / "triggers" / f"{t_id}.json"
        if not t_path.exists():
            t_matches = list((expanded / "triggers").glob(f"{t_id}*.json"))
            if t_matches:
                t_path = t_matches[0]
        trigger = json.load(open(t_path, "r", encoding="utf-8"))

        # Load Customer if present
        customer = None
        if c_id:
            c_path = expanded / "customers" / f"{c_id}.json"
            if not c_path.exists():
                c_matches = list((expanded / "customers").glob(f"{c_id}*.json"))
                if c_matches:
                    c_path = c_matches[0]
            if c_path.exists():
                customer = json.load(open(c_path, "r", encoding="utf-8"))

        # Compose message
        composed = compose(category, merchant, trigger, customer)

        entry = {
            "test_id": test_id,
            "body": composed["body"],
            "cta": composed["cta"],
            "send_as": composed["send_as"],
            "suppression_key": composed["suppression_key"],
            "rationale": composed["rationale"],
        }
        lines.append(json.dumps(entry, ensure_ascii=False))

    with open(out_file, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Successfully generated {len(lines)} outputs in {out_file}")


if __name__ == "__main__":
    main()
