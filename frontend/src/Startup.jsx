import { useState } from "react";

const companies = [
  { code: "RIL_CONSOLIDATED", name: "Reliance Industries (Consolidated)" },
  // later: add JIO_PLATFORMS, RELIANCE_RETAIL, etc.
];

const roles = ["Analyst", "CEO", "Group Management"];

export default function Startup({ onStart }) {
  const [selectedCompany, setSelectedCompany] = useState(companies[0].code);
  const [selectedRole, setSelectedRole] = useState(roles[0]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const c = companies.find((c) => c.code === selectedCompany);
    onStart(c.code, c.name, selectedRole);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%)",
        padding: "20px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Background decorative elements */}
      <div
        style={{
          position: "absolute",
          top: "-50%",
          right: "-10%",
          width: "600px",
          height: "600px",
          background: "radial-gradient(circle, rgba(37, 99, 235, 0.1) 0%, transparent 70%)",
          borderRadius: "50%",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: "-30%",
          left: "-10%",
          width: "500px",
          height: "500px",
          background: "radial-gradient(circle, rgba(37, 99, 235, 0.08) 0%, transparent 70%)",
          borderRadius: "50%",
          pointerEvents: "none",
        }}
      />

      {/* Main content card */}
      <div
        style={{
          maxWidth: "520px",
          width: "100%",
          background: "rgba(26, 26, 46, 0.8)",
          backdropFilter: "blur(10px)",
          borderRadius: "16px",
          padding: "48px",
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.05)",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          position: "relative",
          zIndex: 1,
        }}
      >
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "40px" }}>
          <div
            style={{
              fontSize: "14px",
              fontWeight: "600",
              color: "#4a9eff",
              letterSpacing: "2px",
              textTransform: "uppercase",
              marginBottom: "12px",
            }}
          >
            Financial Analysis Platform
          </div>
          <h1
            style={{
              fontSize: "36px",
              fontWeight: "700",
              color: "#ffffff",
              margin: "0 0 12px 0",
              letterSpacing: "-0.5px",
            }}
          >
            Balance Sheet Chat
          </h1>
          <p
            style={{
              fontSize: "16px",
              color: "rgba(255, 255, 255, 0.7)",
              margin: 0,
              lineHeight: "1.6",
            }}
          >
            Select your company and role to begin financial analysis
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          {/* Company Select */}
          <div style={{ marginBottom: "24px" }}>
            <label
              style={{
                display: "block",
                fontSize: "14px",
                fontWeight: "500",
                color: "#ffffff",
                marginBottom: "8px",
                letterSpacing: "0.3px",
              }}
            >
              Company
            </label>
            <select
              value={selectedCompany}
              onChange={(e) => setSelectedCompany(e.target.value)}
              style={{
                width: "100%",
                padding: "12px 16px",
                fontSize: "15px",
                color: "#ffffff",
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                borderRadius: "8px",
                cursor: "pointer",
                transition: "all 0.3s ease",
                outline: "none",
              }}
              onFocus={(e) => {
                e.target.style.borderColor = "#4a9eff";
                e.target.style.background = "rgba(255, 255, 255, 0.08)";
              }}
              onBlur={(e) => {
                e.target.style.borderColor = "rgba(255, 255, 255, 0.15)";
                e.target.style.background = "rgba(255, 255, 255, 0.05)";
              }}
            >
              {companies.map((c) => (
                <option
                  key={c.code}
                  value={c.code}
                  style={{ background: "#1a1a2e", color: "#ffffff" }}
                >
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          {/* Role Select */}
          <div style={{ marginBottom: "32px" }}>
            <label
              style={{
                display: "block",
                fontSize: "14px",
                fontWeight: "500",
                color: "#ffffff",
                marginBottom: "8px",
                letterSpacing: "0.3px",
              }}
            >
              Role
            </label>
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              style={{
                width: "100%",
                padding: "12px 16px",
                fontSize: "15px",
                color: "#ffffff",
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                borderRadius: "8px",
                cursor: "pointer",
                transition: "all 0.3s ease",
                outline: "none",
              }}
              onFocus={(e) => {
                e.target.style.borderColor = "#4a9eff";
                e.target.style.background = "rgba(255, 255, 255, 0.08)";
              }}
              onBlur={(e) => {
                e.target.style.borderColor = "rgba(255, 255, 255, 0.15)";
                e.target.style.background = "rgba(255, 255, 255, 0.05)";
              }}
            >
              {roles.map((r) => (
                <option
                  key={r}
                  value={r}
                  style={{ background: "#1a1a2e", color: "#ffffff" }}
                >
                  {r}
                </option>
              ))}
            </select>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            style={{
              width: "100%",
              padding: "14px 24px",
              fontSize: "16px",
              fontWeight: "600",
              background: "linear-gradient(135deg, #2563eb 0%, #1e40af 100%)",
              color: "#ffffff",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
              transition: "all 0.3s ease",
              boxShadow: "0 4px 12px rgba(37, 99, 235, 0.3)",
              letterSpacing: "0.3px",
            }}
            onMouseEnter={(e) => {
              e.target.style.background = "linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%)";
              e.target.style.boxShadow = "0 6px 16px rgba(37, 99, 235, 0.4)";
              e.target.style.transform = "translateY(-1px)";
            }}
            onMouseLeave={(e) => {
              e.target.style.background = "linear-gradient(135deg, #2563eb 0%, #1e40af 100%)";
              e.target.style.boxShadow = "0 4px 12px rgba(37, 99, 235, 0.3)";
              e.target.style.transform = "translateY(0)";
            }}
          >
            Start Analysis
          </button>
        </form>
      </div>
    </div>
  );
}
