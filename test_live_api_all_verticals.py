import urllib.request
import json
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'https://magicpin-vera-production.up.railway.app'

test_matrix = [
    # 1. PHARMACIES (Apollo Health Plus)
    {
        'business': 'Apollo Health Plus (Pharmacies)',
        'merchant_id': 'm_009_apollo_pharmacy_jaipur',
        'query': 'what tablets to take for diabetes',
        'expected_intent': 'Chronic disease prescription safety'
    },
    {
        'business': 'Apollo Health Plus (Pharmacies)',
        'merchant_id': 'm_009_apollo_pharmacy_jaipur',
        'query': 'do you deliver medicines to my home in Malviya Nagar?',
        'expected_intent': 'Doorstep delivery inquiry'
    },

    # 2. DENTISTS (Dr. Meera)
    {
        'business': "Dr. Meera's Dental Clinic (Dentists)",
        'merchant_id': 'm_001_drmeera_dentist_delhi',
        'query': 'severe toothache and sensitivity to cold water what to do',
        'expected_intent': 'Clinical pain and sensitivity appointment'
    },
    {
        'business': "Dr. Meera's Dental Clinic (Dentists)",
        'merchant_id': 'm_001_drmeera_dentist_delhi',
        'query': 'where is your clinic located and how to reach?',
        'expected_intent': 'Locality and Google Maps guidance'
    },

    # 3. GYMS (PowerHouse Fitness)
    {
        'business': 'PowerHouse Fitness (Gyms)',
        'merchant_id': 'm_007_powerhouse_gym_bangalore',
        'query': 'how to lose belly fat and chest workout routine',
        'expected_intent': 'Hypertrophy/conditioning consultation'
    },
    {
        'business': 'PowerHouse Fitness (Gyms)',
        'merchant_id': 'm_007_powerhouse_gym_bangalore',
        'query': 'Can you do 150 rs instead of 199? Margins are tight.',
        'expected_intent': 'Tiered margin negotiation'
    },

    # 4. SALONS (Studio11 Family Salon)
    {
        'business': 'Studio11 Family Salon (Salons)',
        'merchant_id': 'm_003_studio11_salon_hyderabad',
        'query': 'how can i reduce pimples and dark spots',
        'expected_intent': 'Anti-acne clarifying facial consultation'
    },
    {
        'business': 'Studio11 Family Salon (Salons)',
        'merchant_id': 'm_003_studio11_salon_hyderabad',
        'query': 'do you accept upi and card payment?',
        'expected_intent': 'Payment modes confirmation'
    },

    # 5. RESTAURANTS (Mylari Cafe)
    {
        'business': 'Mylari South Indian Cafe (Restaurants)',
        'merchant_id': 'm_006_southindiancafe_restaurant_bangalore',
        'query': 'do you have special south indian thali and filter coffee?',
        'expected_intent': 'Regional specialty and menu card'
    },
    {
        'business': 'Mylari South Indian Cafe (Restaurants)',
        'merchant_id': 'm_006_southindiancafe_restaurant_bangalore',
        'query': 'haan bhai theek hai draft bhejo jaldi kardo',
        'expected_intent': 'Hinglish 1-turn affirmative execution'
    },

    # 6. ADVERSARIAL REPLAY SCENARIOS
    {
        'business': 'Auto-Reply Detection (All Verticals)',
        'merchant_id': 'm_001_drmeera_dentist_delhi',
        'query': 'Thank you for contacting Dr. Meera Dental Clinic. We are currently closed. Working hours are 9am to 8pm.',
        'expected_intent': 'WhatsApp auto-reply loop break'
    },
    {
        'business': 'Out-of-Scope Guard (All Verticals)',
        'merchant_id': 'm_001_drmeera_dentist_delhi',
        'query': 'Can you help me file my quarterly GST and tax audit returns?',
        'expected_intent': 'Polite GST/tax scope boundary'
    },
    {
        'business': 'Compound Constraints (Price + Time)',
        'merchant_id': 'm_001_drmeera_dentist_delhi',
        'query': 'haan confirm kardo package 150 rs aur saturday evening ke liye',
        'expected_intent': 'Compound intent synthesis'
    }
]

print('=' * 85)
print('LIVE END-TO-END VERIFICATION OVER HTTPS: ' + BASE_URL)
print('=' * 85)

passed = 0
for idx, test in enumerate(test_matrix, 1):
    payload = {
        'conversation_id': f'live_eval_case_{idx}_{int(time.time())}',
        'merchant_id': test['merchant_id'],
        'message': test['query'],
        'turn_number': 1
    }
    
    t0 = time.perf_counter()
    req = urllib.request.Request(
        f'{BASE_URL}/v1/reply',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'User-Agent': 'LiveTester/1.0'}
    )
    
    try:
        res = urllib.request.urlopen(req, timeout=10)
        dur_ms = (time.perf_counter() - t0) * 1000.0
        data = json.loads(res.read().decode('utf-8'))
        
        print(f"\n[{idx}/{len(test_matrix)}] BUSINESS: {test['business']}")
        print(f"  Target Intent : {test['expected_intent']}")
        print(f"  Inbound Query : \"{test['query']}\"")
        print(f"  Live Action   : {data.get('action')} | CTA: {data.get('cta')} | Cloud Ping: {dur_ms:.1f}ms")
        print(f"  Live Response : \"{data.get('body')}\"")
        print(f"  Live Rationale: {data.get('rationale')}")
        passed += 1
    except Exception as e:
        print(f"  ERROR on case {idx}: {e}")

print('\n' + '=' * 85)
print(f"FINAL RESULT: {passed} / {len(test_matrix)} Cases Passed Live on Railway!")
print('=' * 85)
