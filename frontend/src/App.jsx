import { useEffect, useRef, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const suggestions = [
  "Opening hours",
  "Mutton Karahi price",
  "Delivery charge",
  "Mobile application",
  "Vegetarian dishes",
  "Catering for 200 people",
];

const initialMessages = [
  {
    role: "bot",
    content:
      "Welcome to Bella Vista. Ask about menu items, hours, delivery, reservations, refunds, loyalty, or catering.",
  },
];

function App() {
  const [messages, setMessages] = useState(initialMessages);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function sendQuestion(value) {
    const cleanQuestion = value.trim();
    if (!cleanQuestion || isLoading) return;

    setError("");
    setQuestion("");
    setIsLoading(true);
    setMessages((current) => [
      ...current,
      { role: "user", content: cleanQuestion },
    ]);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: cleanQuestion }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Backend server error.");
      }

      setMessages((current) => [
        ...current,
        {
          role: "bot",
          content: data.answer,
          sources: data.sources || [],
        },
      ]);
    } catch (err) {
      setError(err.message || "Unable to reach the chatbot API.");
      setMessages((current) => [
        ...current,
        {
          role: "bot",
          content:
            "This data does not contain my document.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    sendQuestion(question);
  }

  return (
    <main className="app-shell">
      <style>{styles}</style>

      <aside className="sidebar" aria-label="Knowledge base summary">
        <div className="brand-block">
          <div className="brand-mark">BV</div>
          <div>
            <p className="eyebrow">Bella Vista</p>
            <h1>Restaurant KB</h1>
          </div>
        </div>

        <div className="metric-grid">
          <div>
            <strong>PDF</strong>
            <span>Preloaded</span>
          </div>
          <div>
            <strong>RAG</strong>
            <span>Enabled</span>
          </div>
        </div>

        <section className="side-section">
          <h2>Knowledge Areas</h2>
          <ul>
            <li>Hours and branches</li>
            <li>Menu prices and dishes</li>
            <li>Delivery and refunds</li>
            <li>Reservations and catering</li>
            <li>Loyalty and general FAQs</li>
          </ul>
        </section>

        <section className="side-section">
          <h2>Backend</h2>
          <div className="server-pill">
            <span className="pulse-dot"></span>
            localhost:8000
          </div>
        </section>
      </aside>

      <section className="chat-panel" aria-label="Bella Vista chatbot">
        <header className="chat-header">
          <div>
            <p className="eyebrow">Knowledge Base Chatbot</p>
            <h2>Ask Bella Vista</h2>
          </div>
          <div className="status-pill">
            <span className="pulse-dot"></span>
            Online
          </div>
        </header>

        <div className="suggestions" aria-label="Suggested questions">
          {suggestions.map((item) => (
            <button
              type="button"
              key={item}
              onClick={() => sendQuestion(item)}
              disabled={isLoading}
            >
              {item}
            </button>
          ))}
        </div>

        <div className="messages">
          {messages.map((message, index) => (
            <article
              className={`message-row ${message.role === "user" ? "right" : "left"}`}
              key={`${message.role}-${index}`}
            >
              <div className="avatar" aria-hidden="true">
                {message.role === "user" ? "You" : "AI"}
              </div>
              <div className="message-stack">
                <span className="message-label">
                  {message.role === "user" ? "You" : "Bella Vista Assistant"}
                </span>
                <div className="message-bubble">
                  <p>{message.content}</p>
                  {message.sources?.length > 0 && (
                    <span className="source-text">
                      Source: PDF page {message.sources[0].page || "N/A"}
                    </span>
                  )}
                </div>
              </div>
            </article>
          ))}

          {isLoading && (
            <article className="message-row left">
              <div className="avatar" aria-hidden="true">
                AI
              </div>
              <div className="message-stack">
                <span className="message-label">Bella Vista Assistant</span>
                <div className="message-bubble loading">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </article>
          )}

          <div ref={messagesEndRef} />
        </div>

        {error && <p className="error-message">{error}</p>}

        <form className="composer" onSubmit={handleSubmit}>
          <input
            aria-label="Ask a question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about hours, menu prices, delivery, reservations..."
          />
          <button type="submit" disabled={isLoading || !question.trim()}>
            Send
          </button>
        </form>
      </section>
    </main>
  );
}

const styles = `
:root {
  color: #17201d;
  background: #f3f4f1;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

* { box-sizing: border-box; }
body { margin: 0; min-width: 320px; background: #f3f4f1; }
button, input { font: inherit; }

.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 18px;
  padding: 18px;
  background:
    linear-gradient(135deg, rgba(30, 84, 72, .12), transparent 34%),
    linear-gradient(315deg, rgba(153, 56, 38, .10), transparent 38%),
    #f3f4f1;
}

.sidebar,
.chat-panel {
  border: 1px solid rgba(23, 32, 29, .10);
  background: rgba(255, 255, 255, .94);
  box-shadow: 0 18px 50px rgba(23, 32, 29, .10);
}

.sidebar {
  min-height: calc(100vh - 36px);
  border-radius: 8px;
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #1f5b4d;
  color: #fff;
  font-weight: 800;
  letter-spacing: 0;
}

.eyebrow {
  margin: 0 0 4px;
  color: #a4422f;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1, h2 {
  margin: 0;
  letter-spacing: 0;
  color: #17201d;
}

h1 { font-size: 22px; line-height: 1.15; }
.chat-header h2 { font-size: 24px; line-height: 1.2; }

.metric-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.metric-grid div {
  border: 1px solid rgba(23, 32, 29, .10);
  border-radius: 8px;
  padding: 14px;
  background: #f8faf8;
}

.metric-grid strong,
.metric-grid span {
  display: block;
}

.metric-grid strong {
  font-size: 18px;
  color: #1f5b4d;
}

.metric-grid span {
  margin-top: 4px;
  color: #68736f;
  font-size: 13px;
}

.side-section {
  padding-top: 18px;
  border-top: 1px solid rgba(23, 32, 29, .10);
}

.side-section h2 {
  margin-bottom: 12px;
  font-size: 14px;
}

.side-section ul {
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
  list-style: none;
  color: #52605b;
  font-size: 14px;
}

.side-section li::before {
  content: "";
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 9px;
  border-radius: 50%;
  background: #a4422f;
}

.server-pill,
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  padding: 8px 12px;
  border-radius: 999px;
  background: #edf7f2;
  color: #1f5b4d;
  font-size: 13px;
  font-weight: 800;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #24a267;
  box-shadow: 0 0 0 4px rgba(36, 162, 103, .15);
}

.chat-panel {
  height: calc(100vh - 36px);
  min-height: 640px;
  border-radius: 8px;
  overflow: hidden;
  display: grid;
  grid-template-rows: auto auto 1fr auto auto;
}

.chat-header {
  min-height: 82px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(23, 32, 29, .10);
  background: #fff;
}

.suggestions {
  display: flex;
  gap: 10px;
  padding: 14px 24px;
  overflow-x: auto;
  border-bottom: 1px solid rgba(23, 32, 29, .08);
  background: #fbfcfb;
}

.suggestions button {
  flex: 0 0 auto;
  min-height: 36px;
  border: 1px solid rgba(31, 91, 77, .18);
  border-radius: 999px;
  padding: 0 13px;
  background: #fff;
  color: #1f5b4d;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
}

.suggestions button:disabled {
  cursor: not-allowed;
  opacity: .55;
}

.messages {
  overflow-y: auto;
  padding: 24px;
  background:
    linear-gradient(rgba(31, 91, 77, .035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(31, 91, 77, .035) 1px, transparent 1px),
    #f8f9f6;
  background-size: 28px 28px;
}

.message-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 18px;
}

.message-row.right {
  flex-direction: row-reverse;
}

.avatar {
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #1f5b4d;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
}

.right .avatar {
  background: #a4422f;
}

.message-stack {
  max-width: min(720px, 78%);
}

.right .message-stack {
  display: grid;
  justify-items: end;
}

.message-label {
  display: block;
  margin: 0 0 6px;
  color: #75807c;
  font-size: 12px;
  font-weight: 700;
}

.message-bubble {
  padding: 14px 16px;
  border: 1px solid rgba(23, 32, 29, .08);
  border-radius: 8px;
  background: #fff;
  color: #17201d;
  line-height: 1.55;
  box-shadow: 0 8px 20px rgba(23, 32, 29, .06);
}

.right .message-bubble {
  border-color: rgba(164, 66, 47, .16);
  background: #a4422f;
  color: #fff;
}

.message-bubble p {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.source-text {
  display: block;
  margin-top: 9px;
  color: #66726d;
  font-size: 12px;
}

.right .source-text {
  color: rgba(255, 255, 255, .78);
}

.loading {
  display: flex;
  gap: 7px;
  min-width: 74px;
}

.loading span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #1f5b4d;
  animation: bounce 1s infinite ease-in-out;
}

.loading span:nth-child(2) { animation-delay: .14s; }
.loading span:nth-child(3) { animation-delay: .28s; }

@keyframes bounce {
  0%, 100% { opacity: .35; transform: translateY(0); }
  50% { opacity: 1; transform: translateY(-4px); }
}

.error-message {
  margin: 0;
  padding: 10px 24px;
  border-top: 1px solid rgba(180, 35, 24, .12);
  background: #fff4f2;
  color: #b42318;
  font-size: 13px;
}

.composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 92px;
  gap: 12px;
  padding: 18px 24px;
  border-top: 1px solid rgba(23, 32, 29, .10);
  background: #fff;
}

.composer input {
  width: 100%;
  min-height: 50px;
  border: 1px solid rgba(23, 32, 29, .16);
  border-radius: 8px;
  padding: 0 15px;
  color: #17201d;
  outline: none;
  background: #fbfcfb;
}

.composer input:focus {
  border-color: #1f5b4d;
  box-shadow: 0 0 0 4px rgba(31, 91, 77, .12);
}

.composer button {
  min-height: 50px;
  border: 0;
  border-radius: 8px;
  background: #1f5b4d;
  color: #fff;
  cursor: pointer;
  font-weight: 800;
}

.composer button:disabled {
  cursor: not-allowed;
  opacity: .55;
}

@media (max-width: 900px) {
  .app-shell {
    grid-template-columns: 1fr;
    padding: 0;
  }

  .sidebar {
    display: none;
  }

  .chat-panel {
    height: 100vh;
    min-height: 100vh;
    border: 0;
    border-radius: 0;
  }

  .chat-header {
    padding: 16px;
  }

  .suggestions {
    padding: 12px 16px;
  }

  .messages {
    padding: 16px;
  }

  .message-stack {
    max-width: 82%;
  }

  .composer {
    grid-template-columns: minmax(0, 1fr) 78px;
    padding: 14px 16px;
  }
}
`;

export default App;
