"""
Thread-safe, atomic in-memory context and state store.
Supports versioning, conflict detection, fast query indices, and idempotency.
"""

from __future__ import annotations
import threading
import time
from datetime import datetime, timezone

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

from typing import Dict, Any, Optional, Tuple, List


class ContextStore:
    def __init__(self):
        self._lock = threading.RLock()
        self.start_time = time.time()

        # Context containers: context_id -> payload dict
        self.categories: Dict[str, Dict[str, Any]] = {}
        self.merchants: Dict[str, Dict[str, Any]] = {}
        self.customers: Dict[str, Dict[str, Any]] = {}
        self.triggers: Dict[str, Dict[str, Any]] = {}

        # Version registry: (scope, context_id) -> version int
        self.versions: Dict[Tuple[str, str], int] = {}

        # Secondary indices
        self.customers_by_merchant: Dict[str, List[str]] = {}
        self.triggers_by_merchant: Dict[str, List[str]] = {}
        self.merchants_by_category: Dict[str, List[str]] = {}

        # Conversation tracking: conversation_id -> conversation state dict
        self.conversations: Dict[str, Dict[str, Any]] = {}

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
        Atomically ingests context with version validation.
        Returns: (success, error_reason, current_version)
        """
        valid_scopes = {"category", "merchant", "customer", "trigger"}
        if scope not in valid_scopes:
            return False, "invalid_scope", None

        with self._lock:
            key = (scope, context_id)
            current_version = self.versions.get(key)

            if current_version is not None:
                if version < current_version:
                    # Stale version
                    return False, "stale_version", current_version
                elif version == current_version:
                    # Idempotent no-op (update payload in place)
                    pass

            # Store version
            self.versions[key] = version

            # Store payload by scope
            if scope == "category":
                slug = payload.get("slug", context_id)
                self.categories[slug] = payload
                self.categories[context_id] = payload

            elif scope == "merchant":
                m_id = payload.get("merchant_id", context_id)
                self.merchants[m_id] = payload
                cat = payload.get("category_slug")
                if cat:
                    if cat not in self.merchants_by_category:
                        self.merchants_by_category[cat] = []
                    if m_id not in self.merchants_by_category[cat]:
                        self.merchants_by_category[cat].append(m_id)

            elif scope == "customer":
                c_id = payload.get("customer_id", context_id)
                self.customers[c_id] = payload
                m_id = payload.get("merchant_id")
                if m_id:
                    if m_id not in self.customers_by_merchant:
                        self.customers_by_merchant[m_id] = []
                    if c_id not in self.customers_by_merchant[m_id]:
                        self.customers_by_merchant[m_id].append(c_id)

            elif scope == "trigger":
                t_id = payload.get("id", context_id)
                self.triggers[t_id] = payload
                m_id = payload.get("merchant_id")
                if m_id:
                    if m_id not in self.triggers_by_merchant:
                        self.triggers_by_merchant[m_id] = []
                    if t_id not in self.triggers_by_merchant[m_id]:
                        self.triggers_by_merchant[m_id].append(t_id)

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


# Global singleton instance
store = ContextStore()
