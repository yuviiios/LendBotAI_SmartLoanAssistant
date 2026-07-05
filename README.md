# AI Loan Processing Chatbot

A full-stack AI-assisted personal loan processing system with a conversational chat interface.

## Live Demo
- Frontend: https://loanchatbot.vercel.app/
- Backend API: https://loanchatbot.onrender.com/docs

## What it does
Users interact with a GPT-style chatbot that collects their PAN, monthly income, and loan amount conversationally. The backend runs a deterministic multi-agent pipeline — Sales → KYC → Credit → Sanction — and either approves the loan with an EMI breakdown and downloadable sanction letter, or rejects it with a clear reason.

**Key design principle:** The LLM is used only for natural conversation. All loan decisions are pure Python logic — no AI hallucinations in a financial system.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite |
| Backend | FastAPI, Python 3.12 |
| LLM | Google Gemini 1.5 Flash |
| Testing | pytest, pytest-asyncio |
| Deployment | Render (backend), Vercel (frontend) |

## Architecture

```
Frontend (React)
     │
     ▼
FastAPI (/api/chat)
     │
     ▼
ChatAgent (state machine: PAN → Income → Loan → Confirm → Process)
     │
     ▼
MasterAgent (orchestrator)
     │
     ├── SalesAgent    → validates loan amount & tenure
     ├── KycAgent      → verifies PAN & documents via CRMService
     ├── CreditAgent   → fetches score, calculates EMI, applies rules
     └── SanctionAgent → generates sanction letter file
```

## Running Locally

**Backend:**
```bash
cd backend
python -m venv venv
source venv/Scripts/activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Create `backend/.env`:
```
GEMINI_API_KEY=your_key_here
ALLOWED_ORIGIN=http://localhost:5173
```

## Test PANs

| PAN | Result |
|---|---|
| `ABCDE1234F` | Approved — score 780, all docs present |
| `PQRSX9999Z` | Hold — score 720, missing payslip |
| `LOWSC0000X` | Rejected — score 650, low credit |
| Any other PAN | Failed — KYC not verified |

## Running Tests
```bash
cd backend
pytest
```
22 tests across 6 test files covering all agents and the API endpoint.