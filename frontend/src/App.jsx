import { useState } from "react";
import "./App.css";
import Startup from "./Startup";
import Chat from "./Chat";

function App() {
  const [companyCode, setCompanyCode] = useState(null);
  const [companyName, setCompanyName] = useState(null);
  const [role, setRole] = useState(null);

  if (!companyCode || !role) {
    return (
      <Startup
        onStart={(cCode, cName, r) => {
          setCompanyCode(cCode);
          setCompanyName(cName);
          setRole(r);
        }}
      />
    );
  }

  return (
    <Chat
      companyCode={companyCode}
      companyName={companyName}
      role={role}
      onReset={() => {
        setCompanyCode(null);
        setCompanyName(null);
        setRole(null);
      }}
    />
  );
}

export default App;
