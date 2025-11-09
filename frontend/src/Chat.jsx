import { useState, useEffect, useRef } from "react";
import axios from "axios";
import MetricsChart from "./MetricsChart";

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

export default function Chat({ documentId, companyCode, companyName, fiscalYear, role, onReset, documents = [], onSwitchDocument }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: `You are analyzing ${companyName || "the company"} as a ${role}. Ask anything about its financial performance.`,
      chartData: null,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const backendBaseUrl = "http://127.0.0.1:8000";

  // Reset messages when documentId changes (only on actual change, not on initial mount if already set)
  const prevDocumentIdRef = useRef(documentId);
  useEffect(() => {
    if (documentId && prevDocumentIdRef.current !== documentId) {
      setMessages([
        {
          role: "assistant",
          content: `You are analyzing ${companyName || "the company"} as a ${role}. Ask anything about its financial performance.`,
          chartData: null,
        },
      ]);
      prevDocumentIdRef.current = documentId;
    }
  }, [documentId, companyName, role]);

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
        role,
        messages: newMessages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      };

      // Use document_id if available (upload mode), otherwise use company_code (legacy mode)
      if (documentId) {
        payload.document_id = documentId;
      } else if (companyCode) {
        payload.company_code = companyCode;
      }

      const res = await axios.post(`${backendBaseUrl}/chat/query`, payload);
      const data = res.data;

      setMessages([
        ...newMessages,
        { 
          role: "assistant", 
          content: data.answer,
          chartData: data.chart_data || null,
        },
      ]);
    } catch (err) {
      console.error("Chat error:", err);
      let errorMessage = "Sorry, something went wrong talking to the backend.";
      
      if (err.response) {
        // Server responded with error
        const status = err.response.status;
        if (status === 404) {
          errorMessage = "Document or company not found. Please try uploading again or select a different company.";
        } else if (status === 400) {
          errorMessage = err.response.data?.detail || "Invalid request. Please check your input.";
        } else if (status >= 500) {
          errorMessage = "Server error. Please try again later.";
        } else {
          errorMessage = err.response.data?.detail || errorMessage;
        }
      } else if (err.request) {
        // Request was made but no response received
        errorMessage = "Unable to connect to server. Please check your connection.";
      }
      
      setMessages([
        ...newMessages,
        {
          role: "assistant",
          content: errorMessage,
          chartData: null,
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
            {companyName || "Unknown Company"}
          </div>
          <div style={{ fontSize: "13px", color: "rgba(255, 255, 255, 0.6)", marginTop: "4px" }}>
            {fiscalYear && `Year: ${fiscalYear} • `}Role: {role}
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

      {/* Document Switching Panel */}
      {documents && documents.length > 0 && documentId && onSwitchDocument && (
        <div
          style={{
            padding: "16px 24px",
            background: "rgba(26, 26, 46, 0.4)",
            borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
          }}
        >
          <div
            style={{
              maxWidth: "900px",
              width: "100%",
              margin: "0 auto",
            }}
          >
            <div
              style={{
                fontSize: "13px",
                fontWeight: "500",
                color: "rgba(255, 255, 255, 0.7)",
                marginBottom: "12px",
              }}
            >
              Other Reports
            </div>
            <div
              style={{
                display: "flex",
                gap: "8px",
                overflowX: "auto",
                paddingBottom: "4px",
              }}
            >
              {documents
                .filter((doc) => doc.id !== documentId)
                .slice(0, 5)
                .map((doc) => (
                  <button
                    key={doc.id}
                    onClick={() => onSwitchDocument(doc)}
                    style={{
                      padding: "8px 16px",
                      fontSize: "13px",
                      background: "rgba(255, 255, 255, 0.05)",
                      border: "1px solid rgba(255, 255, 255, 0.1)",
                      color: "#ffffff",
                      borderRadius: "6px",
                      cursor: "pointer",
                      transition: "all 0.3s ease",
                      whiteSpace: "nowrap",
                      flexShrink: 0,
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.background = "rgba(255, 255, 255, 0.1)";
                      e.target.style.borderColor = "rgba(74, 158, 255, 0.4)";
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.background = "rgba(255, 255, 255, 0.05)";
                      e.target.style.borderColor = "rgba(255, 255, 255, 0.1)";
                    }}
                  >
                    {doc.company_name || "Unknown"} • {doc.fiscal_year || "N/A"}
                  </button>
                ))}
            </div>
          </div>
        </div>
      )}

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
                <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
                {m.role === "assistant" && m.chartData && (
                  <div style={{ marginTop: "16px" }}>
                    <MetricsChart chartData={m.chartData} />
                  </div>
                )}
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
