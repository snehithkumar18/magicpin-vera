import urllib.request
import json
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://magicpin-vera-production.up.railway.app'

print('=' * 85)
print('PART 1: TESTING ALL 5 SCENARIO BUTTONS ON THE INTERACTIVE CONSOLE')
print('=' * 85)

scenarios = [
    {
        'button': 'Case 1: Research Digest (/v1/tick)',
        'endpoint': '/v1/tick',
        'payload': {'available_triggers': ['trg_001_research_digest_dentists']}
    },
    {
        'button': 'Scenario 1: WhatsApp Auto-Reply Hell',
        'endpoint': '/v1/reply',
        'payload': {
            'conversation_id': 'conv_autoreply_demo',
            'merchant_id': 'm_001_drmeera_dentist_delhi',
            'message': 'Thank you for contacting Dr. Meera\'s Dental Clinic. We are currently closed. Working hours are 9am to 8pm.',
            'turn_number': 1
        }
    },
    {
        'button': 'Scenario 4: Tight Margin Counter-Offer',
        'endpoint': '/v1/reply',
        'payload': {
            'conversation_id': 'conv_margin_demo',
            'merchant_id': 'm_007_powerhouse_gym_bangalore',
            'message': 'Can you do 150 rs instead of 199? Margins are tight.',
            'turn_number': 1
        }
    },
    {
        'button': 'Scenario 5: Dynamic Hinglish Switch',
        'endpoint': '/v1/reply',
        'payload': {
            'conversation_id': 'conv_hinglish_demo',
            'merchant_id': 'm_006_southindiancafe_restaurant_bangalore',
            'message': 'haan bhai theek hai, thali ka draft bhejo jaldi kardo',
            'turn_number': 1
        }
    },
    {
        'button': 'Scenario 3: GST Scope Guard',
        'endpoint': '/v1/reply',
        'payload': {
            'conversation_id': 'conv_scope_demo',
            'merchant_id': 'm_001_drmeera_dentist_delhi',
            'message': 'Can you help me file my quarterly GST and tax audit returns?',
            'turn_number': 1
        }
    }
]

for idx, s in enumerate(scenarios, 1):
    req = urllib.request.Request(
        f"{BASE}{s['endpoint']}",
        data=json.dumps(s['payload']).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    t0 = time.perf_counter()
    res = urllib.request.urlopen(req)
    dur = (time.perf_counter() - t0) * 1000.0
    data = json.loads(res.read().decode('utf-8'))
    print(f"\n[BUTTON {idx}/5]: {s['button']}")
    print(f"  Endpoint: {s['endpoint']} | Latency: {dur:.1f}ms")
    if 'actions' in data:
        act = data['actions'][0]
        print(f"  Action   : {act.get('send_as')} | CTA: {act.get('cta')}")
        print(f"  Body     : \"{act.get('body')}\"")
        print(f"  Rationale: {act.get('rationale')}")
    else:
        print(f"  Action   : {data.get('action')} | CTA: {data.get('cta')}")
        print(f"  Body     : \"{data.get('body')}\"")
        print(f"  Rationale: {data.get('rationale')}")

print('\n' + '=' * 85)
print('PART 2: TESTING ALL 5 BUSINESS CATEGORIES FROM THE DROPDOWN')
print('=' * 85)

merchants = [
    ("Dr. Meera's Dental Clinic (Dentists)", "m_001_drmeera_dentist_delhi", "trg_001_research_digest_dentists"),
    ("PowerHouse Fitness (Gyms)", "m_007_powerhouse_gym_bangalore", "trg_014_seasonal_acquisition_dip_powerhouse"),
    ("Mylari South Indian Cafe (Restaurants)", "m_006_southindiancafe_restaurant_bangalore", "trg_012_milestone_mylari"),
    ("Studio11 Salon (Salons)", "m_003_studio11_salon_hyderabad", "trg_008_curious_ask_studio11"),
    ("Apollo Health Plus (Pharmacies)", "m_009_apollo_pharmacy_jaipur", "trg_018_supply_atorvastatin_recall")
]

for idx, (m_title, m_id, trg_id) in enumerate(merchants, 1):
    req = urllib.request.Request(
        f"{BASE}/v1/tick",
        data=json.dumps({'available_triggers': [trg_id]}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    t0 = time.perf_counter()
    res = urllib.request.urlopen(req)
    dur = (time.perf_counter() - t0) * 1000.0
    data = json.loads(res.read().decode('utf-8'))
    act = data['actions'][0]
    print(f"\n[DROPDOWN CATEGORY {idx}/5]: {m_title}")
    print(f"  Trigger ID: {trg_id} | Latency: {dur:.1f}ms")
    print(f"  Action    : {act.get('send_as')} | CTA: {act.get('cta')}")
    print(f"  Body      : \"{act.get('body')}\"")
    print(f"  Rationale : {act.get('rationale')}")

print('\n' + '=' * 85)
print('RESULT: ALL 5 SCENARIOS + ALL 5 CATEGORIES (10/10) ARE 100% OPERATIONAL LIVE')
print('=' * 85)
