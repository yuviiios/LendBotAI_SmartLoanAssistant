🔄 Workflow Steps
1️⃣ Fetch KYC Details

The agent retrieves customer KYC data from the CRMService using the provided PAN.

2️⃣ KYC Verification Check

If KYC is not verified → the application fails immediately

No further processing is done for unverified identities

3️⃣ Document Completeness Check

If KYC is verified, the agent checks required documents (e.g., Aadhaar, payslip):

If all required documents are present → proceed

If any documents are missing → mark application as incomplete

4️⃣ KYC Outcome Decision

Based on checks, the agent returns one of the following statuses:

✅ VERIFIED – KYC verified and documents complete

⏸️ INCOMPLETE – KYC verified but documents missing

❌ FAILED – KYC not verified

Each response includes clear reasons or missing document details.

🧠 Key Design Points

No credit or approval logic

No API or database access inside the agent

Uses CRMService only for data retrieval

Fully unit-testable and explainable