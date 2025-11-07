import { useState, useEffect, useRef } from "react";
import axios from "axios";

// Send icon SVG component
const SendIcon = ({ disabled }) => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke={disabled ? "rgba(255, 255, 255, 0.4)" : "currentColor"}
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <line x1="22" y1="2" x2="11" y2="13"></line>
    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
  </svg>
);

export default function Chat({ companyCode, companyName, role, onReset }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: `You are analyzing ${companyName} as a ${role}. Ask anything about its financial performance.`,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const backendBaseUrl = "http://127.0.0.1:8000";

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const newMessages = [...messages, { role: "user", content: input }];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const payload = {
        company_code: companyCode,
        role,
        messages: newMessages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      };

      const res = await axios.post(`${backendBaseUrl}/chat/query`, payload);
      const data = res.data;

      setMessages([
        ...newMessages,
        { role: "assistant", content: data.answer },
      ]);
      setChartData(data.chart_data || null);
    } catch (err) {
      console.error(err);
      setMessages([
        ...newMessages,
        {
          role: "assistant",
          content: "Sorry, something went wrong talking to the backend.",
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        background: "linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%)",
        position: "relative",
      }}
    >
      {/* Header */}
      <header
        style={{
          padding: "20px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "rgba(26, 26, 46, 0.6)",
          backdropFilter: "blur(10px)",
          borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
        }}
      >
        <div>
          <div style={{ fontSize: "16px", fontWeight: "600", color: "#ffffff" }}>
            {companyName}
          </div>
          <div style={{ fontSize: "13px", color: "rgba(255, 255, 255, 0.6)", marginTop: "4px" }}>
            Role: {role}
          </div>
        </div>
        <button
          onClick={onReset}
          style={{
            padding: "8px 16px",
            fontSize: "14px",
            background: "rgba(255, 255, 255, 0.1)",
            border: "1px solid rgba(255, 255, 255, 0.2)",
            color: "#ffffff",
            borderRadius: "6px",
            cursor: "pointer",
            transition: "all 0.3s ease",
          }}
          onMouseEnter={(e) => {
            e.target.style.background = "rgba(255, 255, 255, 0.15)";
          }}
          onMouseLeave={(e) => {
            e.target.style.background = "rgba(255, 255, 255, 0.1)";
          }}
        >
          Change
        </button>
      </header>

      {/* Messages Area - Centered */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "flex-start",
          maxWidth: "900px",
          width: "100%",
          margin: "0 auto",
          padding: "32px 24px",
          overflowY: "auto",
          overflowX: "hidden",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "16px",
            width: "100%",
          }}
        >
          {messages.map((m, idx) => (
            <div
              key={idx}
              style={{
                display: "flex",
                justifyContent: m.role === "user" ? "flex-end" : "flex-start",
                width: "100%",
              }}
            >
              <div
                style={{
                  maxWidth: "75%",
                  padding: "12px 16px",
                  borderRadius: "16px",
                  background:
                    m.role === "user"
                      ? "linear-gradient(135deg, #2563eb 0%, #1e40af 100%)"
                      : "rgba(255, 255, 255, 0.08)",
                  color: "#ffffff",
                  fontSize: "15px",
                  lineHeight: "1.5",
                  wordWrap: "break-word",
                  border:
                    m.role === "assistant"
                      ? "1px solid rgba(255, 255, 255, 0.1)"
                      : "none",
                  boxShadow:
                    m.role === "user"
                      ? "0 2px 8px rgba(37, 99, 235, 0.3)"
                      : "none",
                }}
              >
                {m.content}
              </div>
            </div>
          ))}
          {loading && (
            <div
              style={{
                display: "flex",
                justifyContent: "flex-start",
                width: "100%",
              }}
            >
              <div
                style={{
                  padding: "12px 16px",
                  borderRadius: "16px",
                  background: "rgba(255, 255, 255, 0.08)",
                  color: "rgba(255, 255, 255, 0.6)",
                  fontSize: "15px",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                }}
              >
                Thinking...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Chart Data Display */}
      {chartData && (
        <div
          style={{
            maxWidth: "900px",
            width: "100%",
            margin: "0 auto 16px auto",
            padding: "0 24px",
          }}
        >
          <div
            style={{
              background: "rgba(255, 255, 255, 0.05)",
              borderRadius: "12px",
              padding: "20px",
              border: "1px solid rgba(255, 255, 255, 0.1)",
            }}
          >
            <h3
              style={{
                fontSize: "16px",
                fontWeight: "600",
                color: "#ffffff",
                margin: "0 0 12px 0",
              }}
            >
              Key Metrics
            </h3>
            <p style={{ fontSize: "14px", color: "rgba(255, 255, 255, 0.7)", margin: "0 0 12px 0" }}>
              Years: {chartData.years.join(", ")}
            </p>
            {chartData.series.map((s) => (
              <div
                key={s.label}
                style={{
                  fontSize: "14px",
                  color: "rgba(255, 255, 255, 0.8)",
                  marginBottom: "8px",
                }}
              >
                <strong style={{ color: "#4a9eff" }}>{s.label}:</strong>{" "}
                {s.values.join(", ")}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input Area - Fixed at Bottom */}
      <div
        style={{
          maxWidth: "900px",
          width: "100%",
          margin: "0 auto",
          padding: "20px 24px 32px 24px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            background: "rgba(255, 255, 255, 0.05)",
            borderRadius: "12px",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            padding: "12px 16px",
            gap: "12px",
          }}
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about revenue, profit, trends..."
            disabled={loading}
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              color: "#ffffff",
              fontSize: "15px",
              fontFamily: "inherit",
              resize: "none",
              minHeight: "24px",
              maxHeight: "120px",
              lineHeight: "1.5",
              padding: "0",
            }}
            rows={1}
            onInput={(e) => {
              e.target.style.height = "auto";
              e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
            }}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "40px",
              height: "40px",
              borderRadius: "8px",
              background:
                loading || !input.trim()
                  ? "rgba(255, 255, 255, 0.1)"
                  : "linear-gradient(135deg, #2563eb 0%, #1e40af 100%)",
              border: "none",
              color: "#ffffff",
              cursor: loading || !input.trim() ? "not-allowed" : "pointer",
              transition: "all 0.3s ease",
              flexShrink: 0,
              boxShadow:
                loading || !input.trim()
                  ? "none"
                  : "0 2px 8px rgba(37, 99, 235, 0.3)",
            }}
            onMouseEnter={(e) => {
              if (!loading && input.trim()) {
                e.target.style.background = "linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%)";
                e.target.style.transform = "translateY(-1px)";
              }
            }}
            onMouseLeave={(e) => {
              if (!loading && input.trim()) {
                e.target.style.background = "linear-gradient(135deg, #2563eb 0%, #1e40af 100%)";
                e.target.style.transform = "translateY(0)";
              }
            }}
          >
            <SendIcon disabled={loading || !input.trim()} />
          </button>
        </div>
      </div>
    </div>
  );
}
