"""
magicpin AI Challenge — VERA Message Composition Engine
Official entrypoint module for evaluating compose(...)
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from core.composer import composer


def compose(
    category: Dict[str, Any],
    merchant: Dict[str, Any],
    trigger: Dict[str, Any],
    customer: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Deterministic message composition function for Vera.
    
    Args:
        category: CategoryContext dict
        merchant: MerchantContext dict
        trigger: TriggerContext dict
        customer: CustomerContext dict (optional)
        
    Returns:
        dict with keys:
            - body: str (the WhatsApp message text)
            - cta: str (binary_yes_no, choice, open_ended, none)
            - send_as: str ("vera" or "merchant_on_behalf")
            - suppression_key: str (deduplication key)
            - rationale: str (strategic rationale)
            - template_name: str (optional WhatsApp template name)
            - template_params: list[str] (optional template parameters)
    """
    result = composer.compose(category, merchant, trigger, customer)
    return result.model_dump()


if __name__ == "__main__":
    import json
    from pathlib import Path
    
    # Quick sanity test on Dr. Meera
    dataset_dir = Path(__file__).parent / "expanded"
    cat_file = dataset_dir / "categories" / "dentists.json"
    m_file = dataset_dir / "merchants" / "m_001_drmeera_dentist_delhi.json"
    t_file = dataset_dir / "triggers" / "trg_001_research_digest_dentists.json"
    
    if cat_file.exists() and m_file.exists() and t_file.exists():
        cat = json.load(open(cat_file))
        m = json.load(open(m_file))
        t = json.load(open(t_file))
        
        output = compose(cat, m, t)
        print("\n--- SAMPLE COMPOSED MESSAGE ---")
        print(json.dumps(output, indent=2))
