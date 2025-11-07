import { useState } from "react";
import axios from "axios";

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

  const backendBaseUrl = "http://127.0.0.1:8000";

  const sendMessage = async () => {
    if (!input.trim()) return;

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
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "20px auto", padding: 16 }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 16,
        }}
      >
        <div>
          <strong>{companyName}</strong> | Role: {role}
        </div>
        <button onClick={onReset}>Change company/role</button>
      </header>

      <div
        style={{
          border: "1px solid #ccc",
          borderRadius: 8,
          padding: 16,
          minHeight: 300,
          maxHeight: 500,
          overflowY: "auto",
        }}
      >
        {messages.map((m, idx) => (
          <div
            key={idx}
            style={{
              marginBottom: 8,
              textAlign: m.role === "user" ? "right" : "left",
            }}
          >
            <div
              style={{
                display: "inline-block",
                padding: "8px 12px",
                borderRadius: 16,
                background: m.role === "user" ? "#daf1ff" : "#f1f1f1",
              }}
            >
              {m.content}
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 12 }}>
        <textarea
          rows={2}
          style={{ width: "100%", padding: 8 }}
          placeholder="Ask about revenue, profit, trends..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button onClick={sendMessage} disabled={loading}>
          {loading ? "Thinking..." : "Send"}
        </button>
      </div>

      {chartData && (
        <div style={{ marginTop: 24 }}>
          <h3>Key Metrics</h3>
          <p>Years: {chartData.years.join(", ")}</p>
          {chartData.series.map((s) => (
            <div key={s.label}>
              <strong>{s.label}:</strong> {s.values.join(", ")}
            </div>
          ))}
          {/* Later you can replace this with a real chart library like Recharts */}
        </div>
      )}
    </div>
  );
}
