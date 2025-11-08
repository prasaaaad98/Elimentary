import { useState } from "react";
import "./App.css";
import Startup from "./Startup";
import Chat from "./Chat";

function App() {
  // For upload mode (document_id)
  const [documentId, setDocumentId] = useState(null);
  // For legacy mode (company_code)
  const [companyCode, setCompanyCode] = useState(null);
  const [companyName, setCompanyName] = useState(null);
  const [fiscalYear, setFiscalYear] = useState(null);
  const [role, setRole] = useState(null);
  const [isUploadMode, setIsUploadMode] = useState(false);

  if ((!documentId && !companyCode) || !role) {
    return (
      <Startup
        onStart={(idOrCode, name, r, year, isUpload) => {
          if (isUpload) {
            // Upload mode: idOrCode is document_id
            setDocumentId(idOrCode);
            setIsUploadMode(true);
          } else {
            // Legacy mode: idOrCode is company_code
            setCompanyCode(idOrCode);
            setIsUploadMode(false);
          }
          setCompanyName(name);
          setFiscalYear(year);
          setRole(r);
        }}
      />
    );
  }

  return (
    <Chat
      documentId={documentId}
      companyCode={companyCode}
      companyName={companyName}
      fiscalYear={fiscalYear}
      role={role}
      onReset={() => {
        setDocumentId(null);
        setCompanyCode(null);
        setCompanyName(null);
        setFiscalYear(null);
        setRole(null);
        setIsUploadMode(false);
      }}
    />
  );
}

export default App;
