# LendBot AI

A synthetic personal loan sales demo built with React, FastAPI and LangGraph. The Master coordinates Sales, Verification, Credit and Sanction workers. Customers can compare instalments, confirm terms, verify their demo CRM details and download a PDF sanction letter.

## Run locally

Use Python 3.11+ and Node 22. From `backend`, create a virtual environment, install dependencies with `python -m pip install -r requirements.txt`, copy `.env.example` to `.env`, and run `python -m uvicorn app.main:app --port 8000`. From `frontend`, run `npm ci` and `npm run dev`. Open `http://localhost:5173/?campaign=education`. The default SQLite database persists across process restarts. A Gemini key enables optional model wording. The local demo works with the key empty.

Watch the [recorded browser walkthrough](docs/LendBot-demo.mp4) for the complete journey, the generated PDF and two alternative decisions.

## Demo journey

1. Say **Hello**, then **I need 300000 for course fees**.
2. Use demo PAN **ABCDE1234F** and monthly income **60000**. Compare the 24- and 36-month quotes. Select **24 months** and confirm with **yes**.
3. Enter registered phone **0000000001** and address **11 Demo Lane**.
4. The offer is INR 200,000, so underwriting requests evidence. Download the sample salary slip from chat, then select that PDF in the upload control. The demo verifies the exact customer-specific fixture and obtains the salary from the synthetic payroll record.
5. Download the sanction PDF. Refreshing the same browser tab restores the decision.

For instant approval use the same customer and INR 100,000. For a score rejection use **LOWSC0000X**, phone **0000000003**, address **7 Model Street** and INR 100,000. The fixture file `backend/app/services/customers.csv` contains all ten profiles. Unknown prospects stop at verification. The sales demo uses a fixed annual rate of 14%.

## Policy and persistence

Both entry points invoke the graph in `backend/app/agents/loan_graph.py`. After KYC, a score below 700 or a request above twice the offer limit rejects. A qualifying request within the limit approves instantly. The intermediate band pauses for a slip and approves only when EMI is at most half the verified monthly salary. EMI is rounded half-up to paise.

The SQL application record stores the offer and score used when requesting evidence. Upload resumes the credit node from that snapshot. Approved terms and PDF bytes commit together. Optional direct-API request IDs deduplicate submissions. Chat uses revision checks and a per-session write lease. Browser sessions and application IDs are bearer capabilities intended for synthetic data. Use PostgreSQL and authenticated customer ownership before handling real applications.

## API

FastAPI serves interactive contracts at `/docs`. The mock systems are at `/api/mock/crm/{pan}`, `/api/mock/offers/{pan}` and `/api/mock/bureau/{pan}`. For direct applications send PAN, phone, address, amount, tenure and monthly income to `POST /api/apply-loan`. A pending response includes its application ID. Upload the demo PDF using multipart field `file` at `POST /api/applications/{id}/salary-slip`. Approved documents are served from `GET /api/applications/{id}/letter`.

## Verification and recording

- Backend: from `backend`, run `python -m pytest -q`.
- Frontend: from `frontend`, run `npm run lint` and `npm run build`.
- Browser: from `frontend`, run `npm run test:e2e` with Chrome installed. The suite starts isolated local servers and a temporary SQLite database. Set `LENDBOT_PYTHON` to the Python interpreter with backend dependencies if needed.
- Recording: run `npx playwright install ffmpeg`, set `RECORD_DEMO=1`, and run the browser suite. Videos are written to `frontend/test-results`.

For hosting, set frontend build variable `VITE_API_URL` to the backend origin, backend `ALLOWED_ORIGIN` to the frontend origin, and `DATABASE_URL` to a persistent PostgreSQL database shared by all replicas. A legacy `REDIS_URL` is optional for importing active sessions from earlier versions. Configure it only during that migration.
