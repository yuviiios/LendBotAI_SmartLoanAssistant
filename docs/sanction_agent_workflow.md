🔄 Workflow Steps
1️⃣ Receive Credit Decision

The agent receives a structured decision from the CreditAgent, including:

Approval status

EMI

Credit score

Loan tenure

2️⃣ Sanction Eligibility Check

If credit status is AUTO_APPROVE or CONDITIONAL_APPROVE → eligible for sanction

Any other status (REJECT, HOLD, ESCALATE) → loan is not sanctioned

3️⃣ Generate Sanction Details

For eligible applications, the agent generates:

Unique sanction ID

Sanction timestamp (UTC)

Approved EMI

Approved credit score

Loan terms (interest rate, tenure)

4️⃣ Sanction Outcome

The agent returns one of the following outcomes:

✅ SANCTIONED – Loan officially approved and sanctioned

❌ NOT_SANCTIONED – Loan not eligible for sanction

The response clearly reflects the upstream credit decision.

🧠 Key Design Points

No EMI or credit calculations

No external system calls

Stateless and deterministic

Easy to audit and log