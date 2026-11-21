const fields = [
  { name: "name", label: "Applicant name", placeholder: "Anika Shah", maxLength: 60 },
  { name: "phone", label: "Demo phone (10 digits)", placeholder: "0000000012", inputMode: "numeric", pattern: "[0-9]{10}", maxLength: 10 },
  { name: "address", label: "Demo street address", placeholder: "12 Sample Road", minLength: 3, maxLength: 120 },
  { name: "monthly_salary", label: "Monthly take-home salary (₹)", type: "number", min: 1, max: 10000000 },
  { name: "credit_score", label: "Simulated credit score (0–900)", type: "number", min: 0, max: 900 },
  { name: "preapproved_limit", label: "Simulated pre-approved limit (₹)", type: "number", min: 1, max: 2000000 },
];

export default function CustomProfile({ onStart, onCancel, busy, error }) {
  function submit(event) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const profile = Object.fromEntries(fields.map(({ name, type }) => [
      name, type === "number" ? Number(data.get(name)) : data.get(name).trim(),
    ]));
    onStart(profile);
  }

  return (
    <form className="action-card profile-form" onSubmit={submit} autoComplete="off">
      <h3>Custom customer profile</h3>
      <p>Use fictional details. You’ll confirm this phone and address in chat. Your salary, score and limit determine the simulated outcome.</p>
      <div className="profile-fields">
        {fields.map(({ name, label, ...props }) => (
          <label key={name}>{label}<input name={name} required disabled={busy} {...props} /></label>
        ))}
      </div>
      {error && <p role="alert">{error}</p>}
      <div className="starters">
        <button type="submit" disabled={busy}>Start custom application</button>
        <button type="button" disabled={busy} onClick={onCancel}>Back</button>
      </div>
    </form>
  );
}
