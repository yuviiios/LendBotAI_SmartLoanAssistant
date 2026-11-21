import { useState, useEffect, useRef } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "";

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(() => sessionStorage.getItem("lendbot-session") || crypto.randomUUID());
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
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    sessionStorage.setItem("lendbot-session", sessionId);
    const controller = new AbortController();
    fetch(API_URL + "/api/chat/" + sessionId, { signal: controller.signal })
      .then(response => response.ok ? response.json() : Promise.reject())
      .then(data => {
        revision.current = data.revision;
        setMessages(data.history.map(msg => ({role: msg.role === "user" ? "user" : "bot", text: msg.content})));
        setPending(data.decision?.result?.status === "HOLD" ? data.decision : null);
        setSanctionUrl(data.decision?.result?.document?.download_url || null);
      })
      .catch(() => {})
      .finally(() => { if (!controller.signal.aborted) setIsLoading(false); });
    return () => controller.abort();
  }, [sessionId]);

  async function uploadSlip(file) {
    if (!file || !pending || isLoading) return;
    setIsLoading(true);
    try {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch(API_URL + "/api/applications/" + pending.application_id + "/salary-slip",
        { method: "POST", body });
      const decision = await response.json();
      if (!response.ok) throw new Error(decision.detail || "Upload failed. Please try again.");
      const result = decision.result;
      setMessages(previous => [...previous, {role: "bot", text: result.status === "SANCTIONED"
        ? "Your salary was verified. Approved for ₹" + result.terms.loan_amount.toLocaleString("en-IN") +
          " over " + result.terms.tenure_months + " months. Monthly EMI: ₹" + result.approved_emi.toLocaleString("en-IN") + "."
        : result.reason}]);
      setSanctionUrl(result.document?.download_url || null);
      setPending(null);
    } catch (error) {
      setMessages(previous => [...previous, {role: "bot", text: error.message}]);
    } finally {
      setIsLoading(false);
    }
  }

  function toggleTheme() {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  }

  async function sendMessage() {
    if (!input.trim() || isLoading) return;

    const userMessage = { role: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId, revision: revision.current,
          message: input,
          campaign: ["education", "travel"].includes(new URLSearchParams(location.search).get("campaign"))
            ? new URLSearchParams(location.search).get("campaign") : null,
        }),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Chat request failed.");
      revision.current = data.revision;

      setMessages((prev) => [
        ...prev,
        { role: "bot", text: data.reply || "Something went wrong." },
      ]);

      setPending(data.state?.stage === "AWAITING_SALARY_SLIP" ? data.state.decision : null);
      if (data.sanction_letter_url) {
        setSanctionUrl(data.sanction_letter_url);
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: error.message },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function resetChat() {
    setMessages([]);
    setPending(null);
    setSanctionUrl(null);
    revision.current = 0;
    setIsLoading(true);
    setSessionId(crypto.randomUUID());
  }

  return (
    <div className="app">
      <div className="chat-container">
        {/* Header */}
        <div className="chat-header">
          <div className="header-left">
            <div className="header-logo">L</div>
            <div>
              <div className="header-title">LendBot AI</div>
              <div className="header-subtitle">Smart Loan Assistant</div>
            </div>
          </div>
          <div className="header-actions">
            <button
              className="theme-toggle"
              onClick={toggleTheme}
              aria-label="Toggle theme"
            >
              {theme === "light" ? "🌙" : "☀️"}
            </button>
            <button className="new-chat-btn" onClick={resetChat} disabled={isLoading}>
              New Chat
            </button>
          </div>
        </div>

        {/* Chat Body */}
        <div className="chat-body">
          {messages.length === 0 && !isLoading && (
            <div className="welcome-card">
              <div className="welcome-icon">💰</div>
              <h2>Welcome to LendBot AI</h2>
              <p>
                Get instant loan eligibility checks powered by AI. Just say hi
                to get started!
              </p>
            </div>
          )}

          {messages.map((msg, index) => (
            <div
              key={index}
              className={`message ${msg.role === "user" ? "user" : "bot"}`}
            >
              {msg.text}
            </div>
          ))}

          {isLoading && (
            <div className="typing-indicator">
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
            </div>
          )}

          {pending && (
            <div className="sanction-card">
              <a href={API_URL + pending.sample_slip_url}>Download demo salary slip</a>
              <label>Upload salary slip (PDF)
                <input type="file" accept="application/pdf" disabled={isLoading}
                  onChange={event => { uploadSlip(event.target.files[0]); event.target.value = ""; }} />
              </label>
            </div>
          )}
          {sanctionUrl && (
            <div className="sanction-card">
              <strong>✅ Sanction Letter Ready</strong>
              <br />
              <a
                href={`${API_URL}${sanctionUrl}`}
                target="_blank"
                rel="noreferrer"
              >
                📄 Download Letter
              </a>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="chat-input">
          <input
            type="text"
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            disabled={isLoading}
          />
          <button onClick={sendMessage} disabled={isLoading}>
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
