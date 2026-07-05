🎯 Core Objective

Convert raw user input into a structured loan request that can be processed by KYC and Credit agents.

🔄 Workflow Steps
1️⃣ Capture Customer Requirements

The SalesAgent collects basic loan inputs from the user:

Requested loan amount

Desired tenure

Monthly income

Loan purpose (optional)

This input may come from chat, UI forms, or API requests.

2️⃣ Basic Input Validation

Before forwarding the request, the agent performs sanity checks:

Loan amount is positive and within supported limits

Tenure is within allowed range

Monthly income is provided and reasonable

Invalid or incomplete inputs are corrected or rejected early.

3️⃣ Product Matching

The SalesAgent matches the request against available loan products:

Ensures the loan type supports the requested amount and tenure

Filters out unsupported products

Selects the most suitable product (e.g., personal loan)

This prevents unnecessary failures later in the pipeline.

4️⃣ Suggestion & Optimization (Optional)

To simulate real-world sales behavior, the agent may:

Suggest alternative tenures for suggested EMI reduction

Recommend a slightly adjusted loan amount

Explain trade-offs (lower EMI vs longer tenure)

This step is advisory and does not enforce decisions.

5️⃣ Request Structuring

The SalesAgent converts the validated input into a clean, structured request:

{
  "loan_amount": 200000,
  "tenure_months": 24,
  "monthly_income": 50000,
  "loan_type": "personal_loan"
}


This structured data is ready for downstream processing.

6️⃣ Handoff to Downstream Agents

Once structuring is complete, the SalesAgent forwards the request to:

KYC Agent → identity & document verification

Credit Agent → underwriting & approval logic

At this point, the SalesAgent’s responsibility ends.