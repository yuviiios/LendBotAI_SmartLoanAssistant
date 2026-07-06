# AI Loan Processing Chatbot

End-to-end personal loan application system powered by multi-agent AI architecture. Conversational interface guides customers through KYC, eligibility checks, and sanction letter generation.

## Overview

Customers start a chat, provide PAN/income/loan amount conversationally, and receive instant approval/rejection decisions. Backend uses specialized AI agents that collaborate at each stage:
- **Sales Agent** explains products, validates loan parameters early
- **KYC Agent** validates PAN format real-time, verifies identity
- **Credit Agent** scores, calculates EMI, applies eligibility rules
- **Sanction Agent** generates PDF sanction letters

All loan logic is deterministic (no LLM in financial decisions). LLM only handles conversation naturalness.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite |
| Backend | FastAPI, Python 3.12 |
| LLM | Google Gemini 1.5 Flash (conversation only) |
| NLP | Intent Classification, Entity Extraction (PAN, income, loan amount, tenure) |
| Storage | Redis (session state) |
| Testing | pytest, pytest-asyncio |
| Deployment | Render (backend), Vercel (frontend) |

## Architecture

```
┌─ Frontend (React) ─┐
│  Chat Interface    │
└────────┬───────────┘
         │ /api/chat
         ▼
    FastAPI Router
         │
         ▼
   ChatAgent (orchestrator)
   State machine: PAN → Income → Loan → Tenure → Review → Process
         │
         ├─ Real-time checks:
         │  ├── KYC: PAN format validation
         │  └── Sales: loan parameter validation
         │
         ▼
   MasterAgent (coordinates specialized agents)
         │
         ├── SalesAgent      → product info, loan validation
         ├── KycAgent        → PAN verification, KYC checks
         ├── CreditAgent     → credit score, EMI calc, eligibility
         └── SanctionAgent   → sanction letter generation
         │
         ▼
   External Services
   ├── CRMService         → KYC data lookups
   ├── CreditScoreService → credit score API
   └── PDF Generator      → sanction letter files
```

**Key flow:**
1. User provides PAN → KYC Agent validates format immediately
2. User provides income → Sales Agent context
3. User provides loan amount & tenure → Sales Agent validates parameters
4. User confirms → all agents run sequentially (Sales → KYC → Credit → Sanction)
5. Result: approval/rejection + downloadable sanction letter

## Quick Start

**Backend:**
```bash
cd backend
python -m venv venv
source venv/Scripts/activate  # or: venv\Scripts\activate (Windows)
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here
export REDIS_URL=redis://localhost:6379
export ALLOWED_ORIGIN=http://localhost:5173
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev  # runs on http://localhost:5173
```

## Environment

`backend/.env`:
```env
GEMINI_API_KEY=your_gemini_api_key
REDIS_URL=redis://localhost:6379
ALLOWED_ORIGIN=http://localhost:5173
```

## Agent Collaboration Example

**Conversation flow:**
```
User: "I want a loan"
→ ChatAgent: Asks for PAN

User: "ABCDE1234F"
→ KYC Agent: Validates format ✓
→ ChatAgent: Asks for income

User: "₹50,000"
→ Sales Agent: Acknowledges, continues

User: "I need ₹5 lakh for 24 months"
→ Sales Agent: Validates parameters ✓
→ ChatAgent: Shows review summary

User: "Yes, confirm"
→ Sales Agent: Build loan request
→ KYC Agent: Full verification
→ Credit Agent: Score (780), EMI calc, eligibility check ✓
→ Sanction Agent: Generate sanction letter
→ ChatAgent: Approval + download link
```

## Test PANs

| PAN | Score | Docs | Result |
|---|---|---|---|
| `ABCDE1234F` | 780 | ✓ Complete | **Approved** |
| `PQRSX9999Z` | 720 | Missing payslip | **Hold** |
| `LOWSC0000X` | 650 | N/A | **Rejected** (low score) |
| Any other | N/A | N/A | **Failed** (KYC) |

Try: Loan ₹5,00,000 @ 24 months with income ₹50,000

## Testing

```bash
cd backend
pytest -v                    # Run all tests
pytest tests/test_chat_agent.py -v  # Specific test file
```

22 tests across 6 files covering agents, NLP, APIs, and full flows.

## Project Status

✅ Multi-agent architecture with real-time agent collaboration
✅ Conversational state machine (6 stages)
✅ Real-time parameter validation
✅ Human-in-the-loop review before processing
✅ Sanction letter generation
⏳ Real external APIs (mock services currently)
