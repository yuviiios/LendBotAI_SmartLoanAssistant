import { useState, useEffect, useRef } from "react";
import "./App.css";

// FIX: was hardcoded "http://127.0.0.1:8000" in 2 places.
// Now reads from Vite env variable so dev and prod point to different backends
// automatically — no code change needed between environments.
const API_URL = import.meta.env.VITE_API_URL;

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(crypto.randomUUID());
  const [sanctionUrl, setSanctionUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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

        <div className="chat-header">
          Loan Assistant
          <button className="new-chat-btn" onClick={resetChat}>
            New Chat
          </button>
        </div>

        <div className="chat-body">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`message ${msg.role === "user" ? "user" : "bot"}`}
            >
              {msg.text}
            </div>
          ))}

          {isLoading && (
            <div className="message bot">Processing...</div>
          )}

          {sanctionUrl && (
            <div className="message bot">
              <strong>Sanction Letter Ready</strong>
              <br />
              <a
                href={`${API_URL}${sanctionUrl}`}
                target="_blank"
                rel="noreferrer"
                style={{ color: "#60a5fa" }}
              >
                Download Sanction Letter
              </a>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

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
            {isLoading ? "..." : "Send"}
          </button>
        </div>

      </div>
    </div>
  );
}

export default App;