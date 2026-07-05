🔍 CreditAgent – Decision Flow

The CreditAgent evaluates a loan application and returns a final decision based on creditworthiness, affordability, document status, and policy limits.

It contains only business logic and relies on external services (e.g., credit bureau, CRM) for data retrieval.

🔄 Flow Steps

1️⃣ Fetch Credit Score
    The agent retrieves the applicant’s credit score via CreditScoreService.

2️⃣ Score-Based Eligibility Check
    Credit Score Range	Outcome
    ≥ 750	Eligible for Auto Approval
    700 – 749	Conditionally Eligible
    < 700	Immediate Rejection

3️⃣ EMI Calculation
    The EMI is calculated using the standard banking formula based on:
    Loan amount
    Interest rate
    Loan tenure
    This determines monthly affordability.    

4️⃣ Affordability Check
    If the EMI exceeds 50% of the applicant’s monthly income, the loan is rejected, regardless of credit score.

5️⃣ Document Verification
    ❗ KYC not verified → Escalate for manual review

⏸️ Required documents missing (for conditional scores) → Hold the application
    This avoids unnecessary rejection when issues are fixable.

6️⃣ Loan Amount Policy Check
    If the requested loan amount exceeds 2× the applicant’s annual income, the application is rejected as a policy safeguard.

7️⃣ Final Decision
    If all checks pass, the agent returns a structured decision:
        ✅ AUTO_APPROVE
        ⚠️ CONDITIONAL_APPROVE
        ⏸️ HOLD
        🔍 ESCALATE
        ❌ REJECT

🧠 Key Design Points

🚫 No direct API, database, or FastAPI dependency
🔌 External data accessed via injected services
🧪 Fully unit-testable and explainable decision flow