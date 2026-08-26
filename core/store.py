"""
Persistent, thread-safe context store.
Uses in-memory cache for sub-millisecond reads with atomic disk persistence (JSON/SQLite snapshot)
to ensure state survival across process restarts.
"""

from __future__ import annotations
import threading
import time
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class PersistentContextStore:
    def __init__(self, persistence_file: str = "context_store.json"):
        self._lock = threading.RLock()
        self.start_time = time.time()
        self.persistence_path = Path(__file__).parent.parent / persistence_file

        # Context containers: context_id -> payload dict
        self.categories: Dict[str, Dict[str, Any]] = {}
        self.merchants: Dict[str, Dict[str, Any]] = {}
        self.customers: Dict[str, Dict[str, Any]] = {}
        self.triggers: Dict[str, Dict[str, Any]] = {}

        # Version registry: (scope, context_id) -> version int
        self.versions: Dict[str, int] = {}

        # Secondary indices
        self.customers_by_merchant: Dict[str, List[str]] = {}
        self.triggers_by_merchant: Dict[str, List[str]] = {}
        self.merchants_by_category: Dict[str, List[str]] = {}

        # Conversation tracking
        self.conversations: Dict[str, Dict[str, Any]] = {}

        # Restore from disk if snapshot exists
        self._load_from_disk()

    def _load_from_disk(self):
        """Restores in-memory state from disk snapshot if present."""
        if not self.persistence_path.exists():
            return
        try:
            with open(self.persistence_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.categories = data.get("categories", {})
            self.merchants = data.get("merchants", {})
            self.customers = data.get("customers", {})
            self.triggers = data.get("triggers", {})
            self.versions = data.get("versions", {})
            self.conversations = data.get("conversations", {})
            self._rebuild_indices()
        except Exception:
            pass

    def _persist_to_disk(self):
        """Atomic write to disk to ensure data survives process recycling."""
        try:
            snapshot = {
                "categories": self.categories,
                "merchants": self.merchants,
                "customers": self.customers,
                "triggers": self.triggers,
                "versions": self.versions,
                "conversations": self.conversations,
                "last_persisted": utc_now_iso(),
            }
            tmp_path = self.persistence_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.persistence_path)
        except Exception:
            pass

    def _rebuild_indices(self):
        """Reconstructs secondary lookup indices."""
        self.customers_by_merchant.clear()
        self.triggers_by_merchant.clear()
        self.merchants_by_category.clear()

        for m_id, m in self.merchants.items():
            cat = m.get("category_slug")
            if cat:
                self.merchants_by_category.setdefault(cat, []).append(m_id)

        for c_id, c in self.customers.items():
            m_id = c.get("merchant_id")
            if m_id:
                self.customers_by_merchant.setdefault(m_id, []).append(c_id)

        for t_id, t in self.triggers.items():
            m_id = t.get("merchant_id")
            if m_id:
                self.triggers_by_merchant.setdefault(m_id, []).append(t_id)

    def get_uptime_seconds(self) -> int:
        return int(time.time() - self.start_time)

    def get_counts(self) -> Dict[str, int]:
        with self._lock:
            return {
                "category": len(self.categories),
                "merchant": len(self.merchants),
                "customer": len(self.customers),
                "trigger": len(self.triggers),
            }

    def push_context(
        self,
        scope: str,
        context_id: str,
        version: int,
        payload: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Atomically ingests context with version validation and disk persistence.
        """
        valid_scopes = {"category", "merchant", "customer", "trigger"}
        if scope not in valid_scopes:
            return False, "invalid_scope", None

        with self._lock:
            key = f"{scope}:{context_id}"
            current_version = self.versions.get(key)

            if current_version is not None:
                if version < current_version:
                    return False, "stale_version", current_version

            # Store version
            self.versions[key] = version

            # Store payload
            if scope == "category":
                slug = payload.get("slug", context_id)
                self.categories[slug] = payload
                self.categories[context_id] = payload

            elif scope == "merchant":
                m_id = payload.get("merchant_id", context_id)
                self.merchants[m_id] = payload
                cat = payload.get("category_slug")
                if cat:
                    self.merchants_by_category.setdefault(cat, [])
                    if m_id not in self.merchants_by_category[cat]:
                        self.merchants_by_category[cat].append(m_id)

            elif scope == "customer":
                c_id = payload.get("customer_id", context_id)
                self.customers[c_id] = payload
                m_id = payload.get("merchant_id")
                if m_id:
                    self.customers_by_merchant.setdefault(m_id, [])
                    if c_id not in self.customers_by_merchant[m_id]:
                        self.customers_by_merchant[m_id].append(c_id)

            elif scope == "trigger":
                t_id = payload.get("id", context_id)
                self.triggers[t_id] = payload
                m_id = payload.get("merchant_id")
                if m_id:
                    self.triggers_by_merchant.setdefault(m_id, [])
                    if t_id not in self.triggers_by_merchant[m_id]:
                        self.triggers_by_merchant[m_id].append(t_id)

            # Persist to disk asynchronously / atomically
            self._persist_to_disk()

            return True, None, version

    def get_category(self, slug_or_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.categories.get(slug_or_id)

    def get_merchant(self, merchant_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.merchants.get(merchant_id)

    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.customers.get(customer_id)

    def get_trigger(self, trigger_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.triggers.get(trigger_id)

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.conversations.get(conversation_id)

    def save_conversation(self, conversation_id: str, data: Dict[str, Any]):
        with self._lock:
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = {
                    "conversation_id": conversation_id,
                    "created_at": utc_now_iso(),
                    "turns": [],
                    "state": "active",
                }
            self.conversations[conversation_id].update(data)
            self._persist_to_disk()

    def add_conversation_turn(self, conversation_id: str, turn: Dict[str, Any]):
        with self._lock:
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = {
                    "conversation_id": conversation_id,
                    "created_at": utc_now_iso(),
                    "turns": [],
                    "state": "active",
                }
            self.conversations[conversation_id]["turns"].append(turn)
            self._persist_to_disk()


# Global singleton instance with persistence enabled
store = PersistentContextStore()
