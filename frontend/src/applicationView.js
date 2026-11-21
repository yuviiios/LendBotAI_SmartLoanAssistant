export function applicationView(state = {}, decision = {}, previous = {}) {
  const result = decision?.result || {};
  const approved = result.status === "SANCTIONED";
  const declined = ["FAILED", "INCOMPLETE", "REJECT", "ESCALATE"].includes(
    result.status,
  );
  const closed = state.stage === "CANCELLED" || result.status === "CANCELLED";
  const stage = approved
    ? 4
    : decision?.stage === "CREDIT"
      ? 2
      : decision?.stage === "KYC" ||
          ["COLLECT_PHONE", "COLLECT_ADDRESS"].includes(state.stage)
        ? 1
        : state.stage || decision?.stage
          ? 0
          : previous.stage || 0;
  return {
    stage,
    closed,
    declined,
    approved,
    status: closed
      ? "Closed"
      : declined
        ? "Review outcome"
        : approved
          ? "Approved"
          : result.status === "HOLD"
            ? "Salary slip required"
            : "In progress",
    limit: result.preapproved_limit ?? (approved ? previous.limit : null),
    score: result.score ?? result.approved_score,
    emi: result.emi ?? result.approved_emi,
    amount:
      result.terms?.loan_amount ?? result.loan_amount ?? state.loan_amount,
    tenure: result.terms?.tenure_months ?? result.tenure ?? state.tenure_months,
    rate: result.terms?.interest_rate ?? result.annual_rate ?? 14,
  };
}
