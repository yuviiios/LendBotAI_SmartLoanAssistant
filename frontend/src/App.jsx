import { useState, useEffect, useRef } from "react";
import ApplicationPanel from "./ApplicationPanel";
import { applicationView } from "./applicationView";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "";

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(
    () => sessionStorage.getItem("lendbot-session") || crypto.randomUUID(),
  );
  const [view, setView] = useState(() => applicationView());
  const [pending, setPending] = useState(null);
  const [sanctionUrl, setSanctionUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("lendbot-theme") || "light";
  });
  const revision = useRef(0);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("lendbot-theme", theme);
  }, [theme]);

  useEffect(() => {
    const feed = messagesEndRef.current?.parentElement;
    if (feed) feed.scrollTop = feed.scrollHeight;
  }, [messages, isLoading]);

  useEffect(() => {
    sessionStorage.setItem("lendbot-session", sessionId);
    const controller = new AbortController();
    fetch(API_URL + "/api/chat/" + sessionId, { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((data) => {
        revision.current = data.revision;
        const saved = JSON.parse(
          sessionStorage.getItem("lendbot-view-" + sessionId) || "null",
        );
        setView(
          data.decision?.result
            ? applicationView({}, data.decision, saved || {})
            : saved?.revision === data.revision
              ? saved
              : applicationView(),
        );
        setMessages(
          data.history.map((msg) => ({
            role: msg.role === "user" ? "user" : "bot",
            text: msg.content,
          })),
        );
        setPending(
          data.decision?.result?.status === "HOLD" ? data.decision : null,
        );
        setSanctionUrl(data.decision?.result?.document?.download_url || null);
      })
      .catch(() => {})
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });
    return () => controller.abort();
  }, [sessionId]);

  async function uploadSlip(file) {
    if (!file || !pending || isLoading) return;
    setIsLoading(true);
    try {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch(
        API_URL +
          "/api/applications/" +
          pending.application_id +
          "/salary-slip",
        { method: "POST", body },
      );
      const decision = await response.json();
      if (!response.ok)
        throw new Error(decision.detail || "Upload failed. Please try again.");
      const result = decision.result;
      setView(applicationView({}, decision, view));
      setMessages((previous) => [
        ...previous,
        {
          role: "bot",
          text:
            result.status === "SANCTIONED"
              ? "Your salary was verified. Approved for ₹" +
                result.terms.loan_amount.toLocaleString("en-IN") +
                " over " +
                result.terms.tenure_months +
                " months. Monthly EMI: ₹" +
                result.approved_emi.toLocaleString("en-IN") +
                "."
              : result.reason,
        },
      ]);
      setSanctionUrl(result.document?.download_url || null);
      setPending(null);
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        { role: "bot", text: error.message },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function toggleTheme() {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  }

  async function sendMessage(message = input) {
    if (!message.trim() || isLoading) return;

    const userMessage = { role: "user", text: message };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          revision: revision.current,
          message,
          campaign: ["education", "travel"].includes(
            new URLSearchParams(location.search).get("campaign"),
          )
            ? new URLSearchParams(location.search).get("campaign")
            : null,
        }),
      });

      const data = await response.json();
      if (!response.ok)
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Chat request failed.",
        );
      revision.current = data.revision;

      setMessages((prev) => [
        ...prev,
        { role: "bot", text: data.reply || "Something went wrong." },
      ]);

      const next = applicationView(data.state, data.state?.decision, view);
      setView(next);
      sessionStorage.setItem(
        "lendbot-view-" + sessionId,
        JSON.stringify({ ...next, revision: data.revision }),
      );
      setPending(
        data.state?.stage === "AWAITING_SALARY_SLIP"
          ? data.state.decision
          : null,
      );
      if (data.sanction_letter_url) {
        setSanctionUrl(data.sanction_letter_url);
      }
    } catch (error) {
      setMessages((prev) => [...prev, { role: "bot", text: error.message }]);
    } finally {
      setIsLoading(false);
    }
  }

  function resetChat() {
    sessionStorage.removeItem("lendbot-view-" + sessionId);
    setView(applicationView());
    setMessages([]);
    setPending(null);
    setSanctionUrl(null);
    revision.current = 0;
    setIsLoading(true);
    setSessionId(crypto.randomUUID());
  }

  return (
    <>
      <header className="masthead">
        <div className="wrap header-row">
          <div className="wordmark">
            <span className="brand-mark" aria-hidden="true" />
            <b>LendBot</b>
            <span className="brand-divider" />
            Personal lending
          </div>
          <button
            className="theme"
            onClick={toggleTheme}
            aria-label="Toggle theme"
            title="Toggle theme"
          >
            {theme === "light" ? "◐" : "◑"}
          </button>
        </div>
      </header>
      <main className="wrap">
        <div className="breadcrumb">
          Personal lending <span>/</span> Application workspace
        </div>
        <div className="page-title">
          <div>
            <h1>Personal loan application</h1>
            <p>
              Explore your options and complete your application in one
              conversation.
            </p>
          </div>
          <button className="outline" onClick={resetChat} disabled={isLoading}>
            <span aria-hidden="true">＋</span> New Chat
          </button>
        </div>
        <a className="progress-link" href="#application-progress">
          View application progress ↓
        </a>
        <div className="workspace">
          <section
            className="consultation panel"
            aria-label="Loan consultation"
          >
            <div className="chat-heading">
              <div className="heading-group">
                <span className="consult-icon" aria-hidden="true">
                  ≡
                </span>
                <h2>Loan consultation</h2>
              </div>
              <span className={"status " + (view.approved ? "approved" : "")}>
                {!messages.length ? "New application" : view.status}
              </span>
            </div>
            <div
              className="feed"
              role="log"
              aria-label="Conversation"
              aria-live="polite"
              tabIndex="0"
            >
              <div className="intro">
                <span className="small-label">LENDING ASSISTANT</span>
                <h3>How can I help you today?</h3>
                <p>
                  Tell me what you’re planning and how much you’d like to
                  borrow. I can help you compare monthly repayments and check
                  eligibility.
                </p>
              </div>
              {!messages.length && (
                <div className="starters">
                  {[
                    ["Explore loan options", "Hello"],
                    ["Check interest rates", "What is the interest rate?"],
                    [
                      "Compare repayments",
                      "I need ₹3 lakh and want to compare monthly repayments",
                    ],
                  ].map(([label, prompt]) => (
                    <button
                      key={label}
                      onClick={() => sendMessage(prompt)}
                      disabled={isLoading}
                    >
                      {label}
                      <span aria-hidden="true">↗</span>
                    </button>
                  ))}
                </div>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={"message " + msg.role}>
                  <span className="sender">
                    {msg.role === "user" ? "You" : "Lending assistant"}
                  </span>
                  <div>{msg.text.replace(/\*\*(.*?)\*\*/g, "$1")}</div>
                </div>
              ))}
              {isLoading && (
                <p className="working" role="status">
                  Please wait…
                </p>
              )}
              {pending && (
                <section className="action-card">
                  <span className="small-label">INCOME VERIFICATION</span>
                  <h3>Salary slip required</h3>
                  <a href={API_URL + pending.sample_slip_url}>
                    Download demo salary slip
                  </a>
                  <label>
                    Upload salary slip (PDF)
                    <input
                      type="file"
                      accept="application/pdf"
                      disabled={isLoading}
                      onChange={(event) => {
                        uploadSlip(event.target.files[0]);
                        event.target.value = "";
                      }}
                    />
                  </label>
                </section>
              )}
              {sanctionUrl && (
                <section className="action-card approval">
                  <span className="small-label">APPROVED</span>
                  <h3>Your sanction letter is ready</h3>
                  <a
                    href={API_URL + sanctionUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Download Letter
                  </a>
                </section>
              )}
              <div ref={messagesEndRef} />
            </div>
            <form
              className="composer"
              onSubmit={(e) => {
                e.preventDefault();
                sendMessage();
              }}
            >
              <input
                aria-label="Your message"
                placeholder="Type your message..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isLoading}
              />
              <button type="submit" disabled={isLoading || !input.trim()}>
                Send <span aria-hidden="true">↑</span>
              </button>
            </form>
          </section>
          <ApplicationPanel view={view} />
        </div>
        <footer>
          <span>LendBot AI</span>
          <span>Personal lending workspace</span>
        </footer>
      </main>
    </>
  );
}

export default App;
