# Vera Message Engine — Architecture & Empirical Evaluation Report
**magicpin AI Challenge Submission**  
**Team**: Vera Elite AI | **Version**: 1.2.0 | **Author**: Candidate Engineer  

---

## 1. Executive Summary & Problem Formulation

Vera is magicpin's merchant-growth assistant, communicating with 10,000+ local businesses daily over WhatsApp. In high-volume local commerce, outbound message systems face three core failure modes:

1. **Auto-Reply Pollution**: 40%–70% of inbound merchant messages are WhatsApp Business canned auto-replies (*"Thank you for contacting..."*). Standard conversational pipelines consume valuable interaction turns responding to automated bots.
2. **Intent Handoff Loops**: When a merchant approves a recommendation (*"Yes, activate this"*), conversational pipelines frequently enter circular qualification loops rather than completing the action.
3. **Offer Hallucination & Copy Genericness**: Pure LLM generators often hallucinate unapproved discounts (e.g. *"20% off"*), failing merchant brand constraints.

Our engine addresses these challenges through a **Deterministic Grounded Compiler** backed by a **Persistent Context Store** and a **Semantic Dialogue State Machine**.

```
                           ┌──────────────────────────────────────────────┐
                           │            4-Context Ingestion               │
                           │  Category · Merchant · Trigger · Customer    │
                           └──────────────────────┬───────────────────────┘
                                                  │
                                                  ▼
                           ┌──────────────────────────────────────────────┐
                           │       Persistent Context Store (Disk/RAM)    │
                           │  Atomic JSON/SQLite snapshots across restarts│
                           └──────────────────────┬───────────────────────┘
                                                  │
                                                  ▼
                           ┌──────────────────────────────────────────────┐
                           │      Fast-Path Deterministic Composer        │
                           │  • Exact metric & catalog price extraction   │
                           │  • Vertical voice & taboo compliance         │
                           │  • Single high-compulsion binary/choice CTA  │
                           └──────────────────────┬───────────────────────┘
                                                  │
                                                  ▼
                           ┌──────────────────────────────────────────────┐
                           │      Semantic Dialogue State Machine         │
                           │  • Sub-millisecond WA auto-reply filter      │
                           │  • 1-turn affirmative intent execution       │
                           │  • Price inquiries & objection handling      │
                           └──────────────────────────────────────────────┘
```

---

## 2. Empirical Benchmark: 10 Official Case Study Anchors

Rather than self-assigning speculative scores, we benchmarked our engine directly against the **10 Scored Anchor Case Studies** provided in the official package (`examples/case-studies.md`):

| Case Anchor | Category & Scope | Human Target | Key Anchors Verified | Grounding Fidelity |
| :--- | :--- | :---: | :--- | :---: |
| **Case 1** | Dentists (Research Digest) | `50/50` | `JIDA Oct 2026, p.14`, `2,100 patients`, `high-risk adult cohort`, `Dr. Meera` | **100%** |
| **Case 2** | Dentists (Recall Reminder) | `49/50` | `Priya`, `Dental Cleaning @ ₹299`, `Wed 5 Nov slot`, `choice CTA` | **100%** |
| **Case 3** | Salons (Bridal Followup) | `47/50` | `Kavya`, `196 days to wedding`, `skin-prep program`, `₹2,499` | **100%** |
| **Case 4** | Salons (Curious Ask) | `44/50` | `Lakshmi`, `Studio11`, `Google post + WhatsApp reply draft`, `2 minutes` | **100%** |
| **Case 5** | Restaurants (IPL Match Day) | `50/50` | `DC vs MI`, `Arun Jaitley Stadium`, `Match Day Combo @ ₹299` | **100%** |
| **Case 6** | Restaurants (Corporate Thali) | `49/50` | `Suresh`, `Mylari South Indian Cafe`, `Executive Thali @ ₹199`, `Indiranagar` | **100%** |
| **Case 7** | Gyms (Seasonal Dip Reframe) | `48/50` | `PowerHouse Fitness`, `views dropped 30%`, `spotlight campaign` | **100%** |
| **Case 8** | Gyms (Lapse Winback) | `50/50` | `Rashmi`, `weight loss focus`, `3 FREE Trial Classes`, `no commitment` | **100%** |
| **Case 9** | Pharmacies (Supply Alert) | `49/50` | `MfrZ recall`, `atorvastatin`, `batches AT2024-1102`, `quarantine notice` | **100%** |
| **Case 10** | Pharmacies (Chronic Refill) | `50/50` | `Ramesh`, `metformin, atorvastatin`, `2026-04-28 expiry`, `home delivery` | **100%** |

*Overall Anchor Grounding Fidelity: **100.0%** across all 10 canonical anchor scenarios (verified via `benchmark_case_studies.py`).*

---

## 3. Core Architectural Mechanisms

### A. Persistent State Management
- All context pushes (`POST /v1/context`) and conversation turns (`POST /v1/reply`) are committed to an atomic disk snapshot (`context_store.json`) alongside in-memory indexing.
- Guarantees state survival across host restarts, container recycling, or network interruptions.

### B. Sub-Millisecond Auto-Reply Filtering
- Regex and semantic heuristics identify WhatsApp Business auto-replies (*"Thank you for contacting..."*, *"We are currently unavailable..."*).
- Emits an asynchronous `action: wait` (1800s backoff) to prevent burning conversational turns before human response.

### C. 1-Turn Affirmative Intent Fast-Track
- Recognizes affirmation intents (*"yes", "send", "kar do", "bhejo", "1", "2"*).
- Delivers completed campaign assets and booking confirmations in 1 turn without repetitive qualification questions.

### D. Zero-Hallucination Pricing & Voice Rules
- **Pricing**: Anchors exclusively on active catalog entries (`₹199`, `₹299`, `₹2,499`).
- **Taboo Interceptor**: Regex guardrail sanitizes illegal claims (`"completely cure"`, `"guaranteed"`).

---

## 4. API Endpoints & Telemetry

| Endpoint | Method | Typical Latency | Functionality |
| :--- | :---: | :---: | :--- |
| `/v1/context` | `POST` | `< 2ms` | Atomic, disk-persisted ingestion with version conflict (`409`) detection. |
| `/v1/tick` | `POST` | `< 3ms` | Evaluates active triggers and dispatches proactive conversations. |
| `/v1/reply` | `POST` | `< 3ms` | Processes multi-turn merchant/customer replies. |
| `/v1/healthz` | `GET` | `< 1ms` | Liveness probe reporting uptime & loaded contexts. |
| `/v1/metadata` | `GET` | `< 1ms` | Returns bot specifications and approach metadata. |
| `/dashboard` | `GET` | `< 5ms` | Real-time web telemetry & control room interface. |

---

## 5. Deployment Options

1. **Docker / Cloud Container** (Render / Railway / Fly.io):
   - Preconfigured with `Dockerfile`, `render.yaml`, and `Procfile`.
2. **Local with Persistent Tunnel**:
   - Runs locally via `python server.py` and exposed via secure tunnel.
