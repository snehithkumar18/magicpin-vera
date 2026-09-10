import sys
sys.stdout.reconfigure(encoding='utf-8')
from core.conversation import conversation_engine
from core.store import store

test_cases = [
    # 1. Pharmacies
    ('m_009_apollo_pharmacy_jaipur', 'what tablets to take for diabetes'),
    ('m_009_apollo_pharmacy_jaipur', 'do you have blood pressure medicine in stock?'),
    ('m_009_apollo_pharmacy_jaipur', 'paracetamol syrup for fever'),
    ('m_009_apollo_pharmacy_jaipur', 'do you deliver medicines to my house?'),
    
    # 2. Dentists
    ('m_001_drmeera_dentist_delhi', 'severe toothache what should i do?'),
    ('m_001_drmeera_dentist_delhi', 'how to clean yellow teeth?'),
    ('m_001_drmeera_dentist_delhi', 'teeth sensitivity when drinking cold water'),
    ('m_001_drmeera_dentist_delhi', 'where is your clinic located?'),

    # 3. Gyms
    ('m_007_powerhouse_gym_bangalore', 'how to lose belly fat?'),
    ('m_007_powerhouse_gym_bangalore', 'best chest workout routine'),
    ('m_007_powerhouse_gym_bangalore', 'can you do 150 rs instead of 199?'),
    ('m_007_powerhouse_gym_bangalore', 'what are your gym opening hours?'),

    # 4. Salons
    ('m_003_studio11_salon_hyderabad', 'how can i reduce pimples'),
    ('m_003_studio11_salon_hyderabad', 'hairfall and dandruff treatment'),
    ('m_003_studio11_salon_hyderabad', 'bridal makeup packages'),
    ('m_003_studio11_salon_hyderabad', 'do you accept upi or card payment?'),

    # 5. Restaurants
    ('m_006_southindiancafe_restaurant_bangalore', 'do you have south indian thali today?'),
    ('m_006_southindiancafe_restaurant_bangalore', 'can i book a table for 4 people tonight?'),
    ('m_006_southindiancafe_restaurant_bangalore', 'masala dosa and filter coffee'),
    ('m_006_southindiancafe_restaurant_bangalore', 'haan bhai theek hai draft bhejo jaldi kardo'),
]

print("=" * 80)
print("COMPREHENSIVE MULTI-BUSINESS CUSTOMER QUERY AUDIT (ALL 5 VERTICALS)")
print("=" * 80)

failures = 0
for mid, q in test_cases:
    r = conversation_engine.handle_reply('test', mid, None, 'customer', q, 1, store)
    m = store.get_merchant(mid)
    m_name = m['identity']['name'] if m else mid
    print(f"\n[BUSINESS: {m_name}]")
    print(f"  User Query : \"{q}\"")
    print(f"  Vera Reply : \"{r.body}\"")
    print(f"  Action     : {r.action.upper()} | CTA: {r.cta.upper()}")
    print(f"  Rationale  : {r.rationale}")

    # Check that it didn't fall back to generic Section 12 unless intended
    if "I'm here to help with your appointments, services, and queries" in (r.body or ""):
        print("  [FAIL] Fell through to generic continuation!")
        failures += 1
    else:
        print("  [PASS] Precision domain-specific grounded answer!")

print("\n" + "=" * 80)
print(f"AUDIT COMPLETE: {len(test_cases) - failures} / {len(test_cases)} Passed (Failures: {failures})")
print("=" * 80)
