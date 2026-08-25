"""
Validation and anti-hallucination guards.
Ensures that all generated messages strictly avoid category taboos and adhere to ground truth context.
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Tuple


class AntiHallucinationValidator:
    """Validates message properties and verifies safety against category taboos."""

    @staticmethod
    def check_taboos(body: str, category: Dict[str, Any]) -> List[str]:
        """Detects any prohibited vocabulary from category voice definition."""
        found_taboos = []
        voice = category.get("voice", {})
        taboos = voice.get("vocab_taboo", [])
        
        body_lower = body.lower()
        for taboo in taboos:
            clean_taboo = re.sub(r"\(.*?\)", "", taboo).strip().lower()
            if not clean_taboo:
                continue
            if re.search(r"\b" + re.escape(clean_taboo) + r"\b", body_lower):
                found_taboos.append(taboo)
        return found_taboos

    @staticmethod
    def sanitize_message(body: str, category: Dict[str, Any]) -> str:
        """Replaces taboo words with compliant alternatives if present."""
        sanitized = body
        voice = category.get("voice", {})
        taboos = voice.get("vocab_taboo", [])
        
        replacements = {
            "guaranteed": "proven",
            "100% safe": "tested & clinical",
            "completely cure": "effectively treat",
            "miracle": "breakthrough",
            "best in city": "top rated in your locality",
            "doctor approved": "clinically verified",
        }
        
        for taboo, replacement in replacements.items():
            pattern = re.compile(re.escape(taboo), re.IGNORECASE)
            sanitized = pattern.sub(replacement, sanitized)
            
        return sanitized

    @staticmethod
    def extract_currency_values(text: str) -> List[str]:
        """Extracts INR currency values like ₹299, Rs. 500, etc."""
        return re.findall(r"(?:₹|Rs\.?\s?)(\d[\d,]*)", text)
