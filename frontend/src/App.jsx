import { useState, useEffect, useRef } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL;

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(crypto.randomUUID());
  const [sanctionUrl, setSanctionUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("lendbot-theme") || "light";
  });
  const messagesEndRef = useRef(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("lendbot-theme", theme);
  }, [theme]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

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
          session_id: sessionId,
          message: input,
        }),
      });

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        { role: "bot", text: data.reply || "Something went wrong." },
      ]);

      if (data.sanction_letter_url) {
        setSanctionUrl(data.sanction_letter_url);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "Server error. Please try again later." },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function resetChat() {
    setMessages([]);
    setSanctionUrl(null);
    setSessionId(crypto.randomUUID());
    setIsLoading(false);
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
            <button className="new-chat-btn" onClick={resetChat}>
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
