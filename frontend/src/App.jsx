import { useState, useEffect } from "react";
import axios from "axios";
import "./App.css";
import Startup from "./Startup";
import Chat from "./Chat";

const backendBaseUrl = "http://127.0.0.1:8000";

function App() {
  // Session state - unified structure
  const [session, setSession] = useState(null);
  const [documents, setDocuments] = useState([]);

  // Fetch documents on mount and when needed
  const fetchDocuments = async () => {
    try {
      const res = await axios.get(`${backendBaseUrl}/documents`);
      setDocuments(res.data.documents || []);
    } catch (err) {
      console.error("Failed to load documents list", err);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  // Handle session start (from upload or document selection)
  const handleSessionStart = (idOrCode, name, role, year, isUpload) => {
    if (isUpload) {
      // Upload mode: idOrCode is document_id
      setSession({
        documentId: idOrCode,
        companyCode: null,
        companyName: name,
        fiscalYear: year,
        role: role,
        isUploadMode: true,
      });
      // Refresh documents list after upload
      fetchDocuments();
    } else {
      // Legacy mode: idOrCode is company_code
      setSession({
        documentId: null,
        companyCode: idOrCode,
        companyName: name,
        fiscalYear: year,
        role: role,
        isUploadMode: false,
      });
    }
  };

  // Handle document switching (from Chat component)
  const handleSwitchDocument = (docSummary) => {
    setSession({
      documentId: docSummary.id,
      companyCode: null,
      companyName: docSummary.company_name || "Unknown company",
      fiscalYear: docSummary.fiscal_year || "Unknown period",
      role: session?.role || "Analyst", // Keep same role
      isUploadMode: true,
    });
  };

  // Handle reset (back to startup)
  const handleReset = () => {
    setSession(null);
    // Optionally refresh documents when going back
    fetchDocuments();
  };

  // Show startup if no session
  if (!session) {
    return (
      <Startup
        onStart={handleSessionStart}
        documents={documents}
        onDocumentsReload={fetchDocuments}
      />
    );
  }

  // Show chat if session exists
  return (
    <Chat
      documentId={session.documentId}
      companyCode={session.companyCode}
      companyName={session.companyName}
      fiscalYear={session.fiscalYear}
      role={session.role}
      documents={documents}
      onReset={handleReset}
      onSwitchDocument={handleSwitchDocument}
    />
  );
}

export default App;
