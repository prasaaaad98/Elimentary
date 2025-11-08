import { useState } from "react";
import axios from "axios";

const companies = [
  { code: "RIL_CONSOLIDATED", name: "Reliance Industries (Consolidated)" },
  // later: add JIO_PLATFORMS, RELIANCE_RETAIL, etc.
];

const roles = ["Analyst", "CEO", "Group Management"];

const backendBaseUrl = "http://127.0.0.1:8000";

export default function Startup({ onStart }) {
  const [selectedCompany, setSelectedCompany] = useState(companies[0].code);
  const [selectedRole, setSelectedRole] = useState(roles[0]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [useUpload, setUseUpload] = useState(true); // Default to upload mode

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.type !== "application/pdf") {
        setUploadError("Please select a PDF file");
        setSelectedFile(null);
        // Reset file input
        if (e.target) {
          e.target.value = "";
        }
        return;
      }
      setSelectedFile(file);
      setUploadError(null);
    } else {
      setSelectedFile(null);
    }
  };

  const handleModeToggle = (isUploadMode) => {
    setUseUpload(isUploadMode);
    // Clear state when switching modes
    setSelectedFile(null);
    setUploadError(null);
    // Reset file input if it exists
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
      fileInput.value = "";
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError("Please select a PDF file");
      return;
    }

    setUploading(true);
    setUploadError(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await axios.post(
        `${backendBaseUrl}/upload/balance-sheet`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      const { document_id, company_name, fiscal_year } = response.data;
      onStart(document_id, company_name, selectedRole, fiscal_year, true); // true indicates upload mode
    } catch (error) {
      console.error("Upload error:", error);
      let errorMessage = "Failed to upload PDF. Please try again.";
      
      if (error.response) {
        // Server responded with error
        errorMessage = error.response.data?.detail || errorMessage;
      } else if (error.request) {
        // Request was made but no response received
        errorMessage = "Unable to connect to server. Please check your connection.";
      } else {
        // Something else happened
        errorMessage = error.message || errorMessage;
      }
      
      setUploadError(errorMessage);
      // Clear file selection on error
      setSelectedFile(null);
      const fileInput = document.querySelector('input[type="file"]');
      if (fileInput) {
        fileInput.value = "";
      }
    } finally {
      setUploading(false);
    }
  };

  const handleLegacySubmit = (e) => {
    e.preventDefault();
    const c = companies.find((c) => c.code === selectedCompany);
    onStart(c.code, c.name, selectedRole, null, false); // false indicates legacy mode
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
            Upload a balance sheet PDF or select a demo company to begin analysis
          </p>
        </div>

        {/* Mode Toggle */}
        <div
          style={{
            display: "flex",
            gap: "8px",
            marginBottom: "24px",
            background: "rgba(255, 255, 255, 0.05)",
            borderRadius: "8px",
            padding: "4px",
          }}
        >
          <button
            type="button"
            onClick={() => handleModeToggle(true)}
            style={{
              flex: 1,
              padding: "8px 16px",
              fontSize: "14px",
              fontWeight: "500",
              background: useUpload
                ? "linear-gradient(135deg, #2563eb 0%, #1e40af 100%)"
                : "transparent",
              color: "#ffffff",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              transition: "all 0.3s ease",
            }}
          >
            Upload PDF
          </button>
          <button
            type="button"
            onClick={() => handleModeToggle(false)}
            style={{
              flex: 1,
              padding: "8px 16px",
              fontSize: "14px",
              fontWeight: "500",
              background: !useUpload
                ? "linear-gradient(135deg, #2563eb 0%, #1e40af 100%)"
                : "transparent",
              color: "#ffffff",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              transition: "all 0.3s ease",
            }}
          >
            Demo Company
          </button>
        </div>

        {/* Upload Form */}
        {useUpload ? (
          <form onSubmit={handleUpload}>
            {/* Role Select */}
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

            {/* File Upload */}
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
                Balance Sheet PDF
              </label>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                }}
              >
                <input
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={handleFileChange}
                  disabled={uploading}
                  style={{
                    width: "100%",
                    padding: "12px 16px",
                    fontSize: "15px",
                    color: "#ffffff",
                    background: "rgba(255, 255, 255, 0.05)",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "8px",
                    cursor: uploading ? "not-allowed" : "pointer",
                    transition: "all 0.3s ease",
                    outline: "none",
                  }}
                />
                {selectedFile && (
                  <div
                    style={{
                      fontSize: "13px",
                      color: "rgba(255, 255, 255, 0.7)",
                      padding: "8px 12px",
                      background: "rgba(255, 255, 255, 0.05)",
                      borderRadius: "6px",
                    }}
                  >
                    Selected: {selectedFile.name}
                  </div>
                )}
                {uploadError && (
                  <div
                    style={{
                      fontSize: "13px",
                      color: "#ef4444",
                      padding: "8px 12px",
                      background: "rgba(239, 68, 68, 0.1)",
                      borderRadius: "6px",
                      border: "1px solid rgba(239, 68, 68, 0.3)",
                    }}
                  >
                    {uploadError}
                  </div>
                )}
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={uploading || !selectedFile}
              style={{
                width: "100%",
                padding: "14px 24px",
                fontSize: "16px",
                fontWeight: "600",
                background:
                  uploading || !selectedFile
                    ? "rgba(255, 255, 255, 0.1)"
                    : "linear-gradient(135deg, #2563eb 0%, #1e40af 100%)",
                color: "#ffffff",
                border: "none",
                borderRadius: "8px",
                cursor: uploading || !selectedFile ? "not-allowed" : "pointer",
                transition: "all 0.3s ease",
                boxShadow:
                  uploading || !selectedFile
                    ? "none"
                    : "0 4px 12px rgba(37, 99, 235, 0.3)",
                letterSpacing: "0.3px",
                opacity: uploading || !selectedFile ? 0.6 : 1,
              }}
            >
              {uploading ? "Uploading & Parsing..." : "Upload & Start Analysis"}
            </button>
          </form>
        ) : (
          /* Legacy Company Select Form */
          <form onSubmit={handleLegacySubmit}>
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
        )}
      </div>
    </div>
  );
}
