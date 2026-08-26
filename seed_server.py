"""
High-Speed Dataset Ingestion Tester
Pushes all base dataset contexts concurrently to the server in under 1 second.
"""

from __future__ import annotations
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def push_file(args):
    url, scope, cid, payload = args
    req_body = json.dumps({
        "scope": scope,
        "context_id": cid,
        "version": 1,
        "payload": payload,
    }).encode("utf-8")
    
    req = urllib.request.Request(
        f"{url}/v1/context",
        data=req_body,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return None


import sys

def main():
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    root = Path(__file__).parent / "expanded"
    tasks = []

    # 1. Categories
    for f in (root / "categories").glob("*.json"):
        data = json.load(open(f, "r", encoding="utf-8"))
        cid = data.get("slug", f.stem)
        tasks.append((server_url, "category", cid, data))

    # 2. Merchants
    for f in (root / "merchants").glob("*.json"):
        data = json.load(open(f, "r", encoding="utf-8"))
        cid = data.get("merchant_id", f.stem)
        tasks.append((server_url, "merchant", cid, data))

    # 3. Customers
    for f in (root / "customers").glob("*.json"):
        data = json.load(open(f, "r", encoding="utf-8"))
        cid = data.get("customer_id", f.stem)
        tasks.append((server_url, "customer", cid, data))

    # 4. Triggers
    for f in (root / "triggers").glob("*.json"):
        data = json.load(open(f, "r", encoding="utf-8"))
        cid = data.get("id", f.stem)
        tasks.append((server_url, "trigger", cid, data))

    print(f"Pushing {len(tasks)} contexts concurrently...")
    with ThreadPoolExecutor(max_workers=20) as executor:
        list(executor.map(push_file, tasks))

    # Check Healthz
    req = urllib.request.Request(f"{server_url}/v1/healthz")
    with urllib.request.urlopen(req, timeout=5) as resp:
        health = json.loads(resp.read().decode("utf-8"))
        print("\n--- Healthz Response ---")
        print(json.dumps(health, indent=2))


if __name__ == "__main__":
    main()
