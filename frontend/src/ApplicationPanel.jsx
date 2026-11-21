const currency = (value) =>
  "₹" + Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 });
const stages = [
  "Loan consultation",
  "KYC verification",
  "Underwriting",
  "Sanction letter",
];
const descriptions = [
  "Discuss your needs and terms",
  "Confirm your registered details",
  "Review eligibility and income",
  "Receive your approval document",
];

export default function ApplicationPanel({ view }) {
  const {
    stage,
    approved,
    closed,
    declined,
    limit,
    score,
    emi,
    amount,
    tenure,
    rate,
  } = view;
  return (
    <aside aria-label="Application overview">
      <section
        className="progress panel"
        id="application-progress"
        tabIndex="-1"
      >
        <div className="section-heading">
          <h2>Application progress</h2>
          <span className="counter">{Math.min(stage + 1, 4)} / 4</span>
        </div>
        <ol>
          {stages.map((label, i) => {
            const complete = i < stage,
              current = i === stage;
            return (
              <li
                key={label}
                className={complete ? "complete" : current ? "current" : ""}
                aria-current={current ? "step" : undefined}
              >
                <span className="step-mark" aria-hidden="true">
                  {complete ? "✓" : String(i + 1).padStart(2, "0")}
                </span>
                <div>
                  <strong>{label}</strong>
                  <small>
                    {current && (closed || declined)
                      ? view.status
                      : descriptions[i]}
                  </small>
                </div>
              </li>
            );
          })}
        </ol>
      </section>
      <section className="terms" aria-label="Loan terms">
        <div className="terms-title">
          <span className="small-label">
            {limit
              ? "YOUR PRE-APPROVED LIMIT"
              : approved
                ? "APPROVED AMOUNT"
                : amount
                  ? "REQUESTED AMOUNT"
                  : "PERSONAL LOAN"}
          </span>
          <strong>
            {limit
              ? currency(limit)
              : amount
                ? currency(amount)
                : "₹50,000 – ₹20 lakh"}
          </strong>
          {!limit && !amount && <small>Product amount range</small>}
        </div>
        <div className="terms-grid">
          <div>
            <span>Annual rate</span>
            <b>{rate}%</b>
          </div>
          <div>
            <span>Tenure</span>
            <b>
              {tenure || "6–60"} <small>months</small>
            </b>
          </div>
        </div>
      </section>
      {(emi != null || score != null || approved) && (
        <section className="financial panel">
          <h2>Decision summary</h2>
          <dl>
            {approved && (
              <>
                <dt>Status</dt>
                <dd className="success">Approved</dd>
              </>
            )}
            {score != null && (
              <>
                <dt>Credit score</dt>
                <dd>{score} / 900</dd>
              </>
            )}
            {amount != null && (
              <>
                <dt>Principal</dt>
                <dd>{currency(amount)}</dd>
              </>
            )}
            {emi != null && (
              <>
                <dt>Monthly EMI</dt>
                <dd>{currency(emi)}</dd>
              </>
            )}
            {emi != null && tenure && (
              <>
                <dt>Total instalments¹</dt>
                <dd>{currency(emi * tenure)}</dd>
              </>
            )}
          </dl>
          {emi != null && tenure && (
            <small>¹ Based on rounded EMI, before fees.</small>
          )}
        </section>
      )}
    </aside>
  );
}
